# Shared project-style.json, read by native R plotting and exports.
.lc_style_env <- new.env(parent = emptyenv())
.lc_style_script <- local({
  paths <- vapply(sys.frames(), function(x) if (is.null(x$ofile)) "" else as.character(x$ofile)[1], character(1))
  matches <- paths[basename(paths) == "project_style.R"]
  dirname(normalizePath(tail(matches, 1), mustWork = TRUE))
})

use_project_style <- function(path = file.path(.lc_style_script, "..", "assets", "project-style.json")) {
  if (!requireNamespace("jsonlite", quietly=TRUE)) stop("jsonlite required")
  x <- jsonlite::read_json(path, simplifyVector=TRUE)
  if (!identical(x$schema_version, 1L)) stop("Unsupported project-style schema")
  if (!all(c('fonts','typography','roles','palettes','groups','metrics') %in% names(x))) stop('Missing project objects')
  if (!all(c('latin','cjk','serif') %in% names(x$fonts)) ||
      any(!nzchar(unlist(x$fonts[c('latin','cjk')]))) || !is.logical(x$fonts$serif)) stop('Invalid font configuration')
  if (!all(c('base_pt','minimum_pt','heading_pt') %in% names(x$typography)) ||
      any(!is.finite(unlist(x$typography))) || min(unlist(x$typography)) <= 0 ||
      min(x$typography$base_pt,x$typography$heading_pt) < x$typography$minimum_pt) stop("Invalid typography")
  required <- c("ink","muted","baseline","primary","secondary","accent","pale","missing","down","up")
  if (!all(required %in% names(x$roles))) stop("Missing semantic colors")
  all_colors <- c(unlist(x$roles),unlist(x$palettes),vapply(x$groups,function(g)g$color,character(1)))
  tryCatch(grDevices::col2rgb(all_colors),error=function(e)stop("Invalid project colors"))
  if (length(x$palettes$categorical)<1 || length(x$palettes$sequential)<2 || length(x$palettes$diverging)!=3) stop("Invalid palettes")
  if (length(x$metrics) && any(!vapply(x$metrics,function(m)length(m$direction)==1L && m$direction %in% c('min','max','none'),logical(1))))
    stop('Metric direction must be min/max/none')
  x$source_path <- normalizePath(path, mustWork=TRUE)
  .lc_style_env$project <- x
  invisible(x)
}

lc_project <- function() {
  if (!exists("project",envir=.lc_style_env,inherits=FALSE)) use_project_style()
  .lc_style_env$project
}
lc_color <- function(name) lc_project()$roles[[name]]
lc_colors <- function(labels) {
  p <- lc_project(); labels <- as.character(labels)
  if (length(p$groups)) {
    if (!all(labels %in% names(p$groups))) stop("Unmapped project groups")
    return(setNames(vapply(labels,function(k)p$groups[[k]]$color,character(1)),labels))
  }
  if (length(labels)>length(p$palettes$categorical)) stop("Define explicit named colors; do not recycle")
  setNames(p$palettes$categorical[seq_along(labels)],labels)
}
lc_encodings <- function(labels) {
  p <- lc_project(); colors <- lc_colors(labels)
  setNames(lapply(as.character(labels),function(k) {
    x <- p$groups[[k]]; if(is.null(x))x<-list()
    x$color <- unname(colors[[k]]); x
  }),as.character(labels))
}
lc_fonts <- function() {
  p <- lc_project(); available <- unique(systemfonts::system_fonts()$family)
  latin <- c(p$fonts$latin,if(isTRUE(p$fonts$serif))"Times New Roman" else "Arial",if(isTRUE(p$fonts$serif))'DejaVu Serif' else 'DejaVu Sans')
  cjk <- c(p$fonts$cjk,"Microsoft YaHei","SimSun","Noto Sans CJK SC")
  list(latin=latin[latin %in% available][1],cjk=cjk[cjk %in% available][1])
}

# Explicit runs keep Latin digits in the Latin face even inside Chinese labels.
# cairo_pdf/ragg retain native text; no conversion to bitmap or glyph outlines.
mixed_text_grob <- function(label,x=grid::unit(.5,"npc"),y=grid::unit(.5,"npc"),
                            fontsize=lc_project()$typography$base_pt,hjust=0,color=lc_color("ink")) {
  if (length(label)!=1L || is.na(label)) stop("A single nonmissing label is required")
  if (!nzchar(label)) return(grid::nullGrob())
  fonts <- lc_fonts(); chars <- strsplit(enc2utf8(label),"")[[1]]
  chinese <- grepl("[\\x{2E80}-\\x{9FFF}]",chars,perl=TRUE)
  runs <- rle(chinese); ends <- cumsum(runs$lengths); starts <- ends-runs$lengths+1L
  pieces <- lapply(seq_along(starts),function(i)paste0(chars[starts[i]:ends[i]],collapse=""))
  grobs <- lapply(seq_along(pieces),function(i) {
    family <- if(runs$values[i])fonts$cjk else fonts$latin
    if (is.na(family)) stop("Required font not installed")
    grid::textGrob(pieces[[i]],just=c("left","centre"),gp=grid::gpar(fontfamily=family,fontsize=fontsize,col=color))
  })
  widths <- lapply(grobs,grid::grobWidth); total <- Reduce(`+`,widths)
  offset <- grid::unit(0,"pt")
  for (i in seq_along(grobs)) {
    grobs[[i]]$x <- x-hjust*total+offset; grobs[[i]]$y <- y
    offset <- offset+widths[[i]]
  }
  grid::gTree(children=do.call(grid::gList,grobs))
}

# Cairo on Windows can retain Chinese Unicode in extraction while embedding
# missing Arial glyphs. Render mixed ggplot/grid labels as explicit font runs.
lc_native_text <- function(grob) {
  if (inherits(grob,'text') && is.character(grob$label) &&
      any(vapply(grob$label,function(x)any(utf8ToInt(enc2utf8(x))>127L),logical(1)))) {
    if (!requireNamespace('gridtext',quietly=TRUE))
      stop('Mixed Chinese/Latin ggplot export requires gridtext')
    fonts <- lc_fonts()
    escape <- function(x) {
      x <- gsub('&','&amp;',x,fixed=TRUE);x <- gsub('<','&lt;',x,fixed=TRUE)
      x <- gsub('>','&gt;',x,fixed=TRUE)
      for (key in c('*','_','`','[',']','\\')) {
        x <- gsub(key,paste0('&#',utf8ToInt(key),';'),x,fixed=TRUE)
      }
      gsub('\n','<br>',x,fixed=TRUE)
    }
    markup <- vapply(grob$label,function(label) {
      chars <- strsplit(enc2utf8(label),'')[[1]]
      is_cjk <- grepl('[\u2E80-\u9FFF]',chars)
      available <- unique(systemfonts::system_fonts()$family)
      families <- rep(fonts$latin,length(chars))
      missing <- systemfonts::glyph_info(chars,family=fonts$latin)$index==0
      for(i in which(is_cjk | missing)) {
        candidates <- unique(c(if(is_cjk[i])fonts$cjk,fonts$latin,'Calibri','Segoe UI Symbol','Cambria Math',fonts$cjk))
        candidates <- candidates[!is.na(candidates) & candidates %in% available]
        supported <- vapply(candidates,function(f)systemfonts::glyph_info(chars[i],family=f)$index[1]!=0,logical(1))
        if(!any(supported))stop('No installed font supports a required scientific/CJK glyph')
        families[i] <- candidates[which(supported)[1]]
      }
      paste0(ifelse(families!=fonts$latin,paste0('<span style="font-family:',families,';">',escape(chars),'</span>'),escape(chars)),collapse='')
    },character(1))
    just <- function(x) {
      if (is.numeric(x)) return(x)
      value <- c(left=0,bottom=0,centre=.5,center=.5,right=1,top=1)[x]
      ifelse(is.na(value),.5,value)
    }
    gp <- if(is.null(grob$gp)) grid::gpar() else grob$gp
    gp$fontfamily <- fonts$latin
    return(gridtext::richtext_grob(markup,x=grob$x,y=grob$y,
      hjust=if(is.null(grob$hjust))just(grob$just[1]) else grob$hjust,
      vjust=if(is.null(grob$vjust))just(tail(grob$just,1)) else grob$vjust,
      rot=grob$rot,gp=gp,name=grob$name,
      padding=grid::unit(rep(0,4),'pt'),margin=grid::unit(rep(0,4),'pt')))
  }
  if (length(grob$grobs)) grob$grobs <- lapply(grob$grobs,lc_native_text)
  if (length(grob$children)) {
    grob$children <- do.call(grid::gList,lapply(grob$children,lc_native_text))
  }
  grob
}
