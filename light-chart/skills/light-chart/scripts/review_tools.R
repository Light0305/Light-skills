# Native ggplot layer snapshots. Coordinates are built by R, never redrawn in Python.
figure_snapshot_r <- function(plots) {
  if (inherits(plots,'ggplot') || inherits(plots,'patchwork'))
    stop('Pass a named list of the actual component ggplots; patchwork is not a single panel')
  if (!length(plots) || is.null(names(plots)) || anyDuplicated(names(plots))) stop('Named component plots required')
  panels <- list(); identities <- list()
  for (key in names(plots)) {
    p <- plots[[key]]
    if (!inherits(p,'ggplot') || inherits(p,'patchwork')) stop('Each component must be a native ggplot')
    b <- ggplot2::ggplot_build(p)
    for (pid in b$layout$layout$PANEL) {
      id <- if(nrow(b$layout$layout)==1)key else paste0(key,'[',pid,']')
      marks <- list(); classes <- character()
      for (i in seq_along(b$data)) {
        layer <- b$data[[i]]; layer <- layer[as.character(layer$PANEL)==as.character(pid),,drop=FALSE]
        geom <- class(p$layers[[i]]$geom)[1]; classes <- c(classes,geom)
        # Position, grouping, computed statistics and weights are evidence.
        cosmetic <- c('colour','color','fill','alpha','shape','linetype','linewidth','size','stroke')
        fields <- setdiff(names(layer),cosmetic)
        marks[[paste0(geom,':',i)]] <- lapply(layer[fields], function(x) {
          if(is.factor(x))as.character(x) else unname(x)
        })
        # All rendered mapped/cosmetic channels separately, so deliberate palette
        # changes require explanation while data/geometry changes stay detectable.
        identities[[paste0(id,'/',i)]] <- lapply(layer[intersect(names(layer),cosmetic)],unname)
      }
      scale_name <- function(axis) {
        index <- b$layout$layout[[paste0('SCALE_',toupper(axis))]][match(pid,b$layout$layout$PANEL)]
        s <- b$layout[[paste0('panel_scales_',axis)]][[index]]
        if(inherits(s,'ScaleDiscrete'))'discrete' else s$get_transformation()$name
      }
      view <- b$layout$panel_params[[match(pid,b$layout$layout$PANEL)]]
      panels[[id]] <- list(marks=marks,xscale=scale_name('x'),yscale=scale_name('y'),
        view_limits=list(x=view$x.range,y=view$y.range),
        artist_classes=sort(unique(classes)))
    }
    # Preserve label -> aesthetic mapping as well as row-wise aesthetic values.
    for (aesthetic in c('colour','fill','shape','linetype','size','alpha')) {
      s <- b$plot$scales$get_scales(aesthetic)
      if (!is.null(s)) identities[[paste0(key,'/scale/',aesthetic)]] <- list(
        limits=unname(s$get_limits()), mapped=unname(s$map(s$get_limits())))
    }
  }
  list(panels=panels,named_series_colors=identities,backend='R/ggplot2',schema_version=1L)
}

audit_marks_r <- function(plots) {
  findings <- list()
  for(key in names(plots)) {
    b <- ggplot2::ggplot_build(plots[[key]])
    for(pid in b$layout$layout$PANEL) {
      id <- if(nrow(b$layout$layout)==1)key else paste0(key,'[',pid,']')
      view <- b$layout$panel_params[[match(pid,b$layout$layout$PANEL)]]
      for(i in seq_along(b$data)) {
        d <- b$data[[i]];d<-d[as.character(d$PANEL)==as.character(pid),,drop=FALSE]
        outside<-rep(FALSE,nrow(d))
        for(axis in c('x','y')) {
          limits<-view[[paste0(axis,'.range')]]
          for(field in intersect(c(axis,paste0(axis,c('min','max','end'))),names(d))) {
            values<-as.numeric(d[[field]])
            outside<-outside | (is.finite(values) & (values<limits[1]-1e-8 | values>limits[2]+1e-8))
          }
        }
        if(any(outside))findings[[length(findings)+1L]]<-list(code='data_clipped',panel=id,
          mark=paste0(class(plots[[key]]$layers[[i]]$geom)[1],':',i),count=sum(outside),severity='WARN')
      }
    }
  }
  findings
}

source_manifest_r <- function(paths) {
  if (!requireNamespace('digest',quietly=TRUE))stop('digest required for source SHA-256')
  if (!is.character(paths) || !length(paths)) stop('source_files must contain file paths')
  if (is.null(names(paths)))names(paths)<-basename(paths)
  if (anyNA(names(paths)) || any(!nzchar(trimws(names(paths)))) || anyDuplicated(names(paths)))
    stop('Source names must be nonempty and unique; use named source_files')
  setNames(lapply(paths,function(path) {
    path<-normalizePath(path,winslash='/',mustWork=TRUE)
    if (dir.exists(path)) stop('Source must be a file')
    list(path=path,sha256=digest::digest(file=path,algo='sha256'),bytes=file.info(path)$size)
  }),names(paths))
}
