# R draws/exports; Python corrects Cairo page rounding and inspects PDF/geometry.
.light_chart_dir <- local({
  source_paths <- vapply(sys.frames(), function(frame) {
    if (is.null(frame$ofile)) "" else as.character(frame$ofile)[1]
  }, character(1))
  candidates <- source_paths[basename(source_paths) == "publication.R"]
  if (!length(candidates)) stop("Load publication.R with source()", call. = FALSE)
  source_path <- tail(candidates, 1)
  dirname(normalizePath(source_path, mustWork = TRUE))
})
source(file.path(.light_chart_dir, "panel_alignment.R"))
source(file.path(.light_chart_dir, "project_style.R"))
source(file.path(.light_chart_dir, "review_tools.R"))

light_chart_family <- function(lang = "en") {
  if (!lang %in% c('en','zh')) stop('lang must be en or zh')
  fonts <- lc_fonts()
  if (lang=='zh' && is.na(fonts$cjk)) stop('Required Chinese font not installed')
  fonts$latin
}

theme_light_chart <- function(base_size = lc_project()$typography$base_pt, lang = "en", family = light_chart_family(lang)) {
  ggplot2::theme_classic(base_size = base_size, base_family = family) +
    ggplot2::theme(
      axis.text = ggplot2::element_text(size=base_size),
      legend.text = ggplot2::element_text(size=base_size),
      axis.line = ggplot2::element_line(linewidth = 0.35, colour = "#333333"),
      axis.ticks = ggplot2::element_line(linewidth = 0.3),
      plot.title = ggplot2::element_text(face = "bold", size = base_size + 1),
      plot.tag = ggplot2::element_text(face = "bold", size = base_size + 1),
      legend.title = ggplot2::element_blank(), legend.key = ggplot2::element_blank(),
      plot.margin = ggplot2::margin(8, 8, 8, 8)
    )
}

save_figure_r <- function(plot, basename, width_mm = 180, height_mm = 120,
                          dpi = 300, lang = "en", python = Sys.which("python"),
                          min_font_pt = lc_project()$typography$minimum_pt, alignment_options = list(), tiff = FALSE,
                          draw = function(object) print(object), review_plots = NULL,
                          source_files = NULL, data_sources = NULL) {
  default_draw <- missing(draw)
  if (!is.function(draw)) stop("draw must be a function accepting the plot object", call. = FALSE)
  for (package in c("svglite", "ragg", "jsonlite")) {
    if (!requireNamespace(package, quietly = TRUE)) stop(sprintf("Missing R package: %s", package), call. = FALSE)
  }
  if (any(!is.finite(c(width_mm, height_mm, dpi))) || min(width_mm, height_mm, dpi) <= 0) {
    stop("Dimensions and DPI must be finite and positive", call. = FALSE)
  }
  source_manifest <- if (is.null(source_files)) NULL else source_manifest_r(source_files)
  if (!is.null(data_sources) && (!is.character(data_sources) || !length(data_sources) ||
      anyNA(data_sources) || anyDuplicated(data_sources) ||
      any(!data_sources %in% names(source_manifest)))) {
    stop("data_sources must name the actual data entries in source_files",call.=FALSE)
  }
  dir.create(dirname(basename), recursive = TRUE, showWarnings = FALSE)
  width <- width_mm / 25.4
  height <- height_mm / 25.4
  family <- light_chart_family(lang)
  if (default_draw && (inherits(plot,'ggplot') || inherits(plot,'patchwork'))) {
    draw <- function(object) {
      grid::grid.newpage()
      grob <- if(inherits(object,'patchwork')) patchwork::patchworkGrob(object) else ggplot2::ggplotGrob(object)
      grid::grid.draw(lc_native_text(grob))
    }
  }
  qa_path <- paste0(basename, ".qa.json")
  jsonlite::write_json(list(automated_status = "IN_PROGRESS", visual_review = list(status = "pending")),
                       qa_path, auto_unbox = TRUE, pretty = TRUE)
  needs_alignment <- inherits(plot,'patchwork') || (inherits(plot,'ggplot') &&
    nrow(ggplot2::ggplot_build(plot)$layout$layout)>1L)
  if (needs_alignment) {
    tryCatch(do.call(require_patchwork_panel_alignment, c(list(
      plot = plot, manifest_path = paste0(basename, ".alignment-layout.json"),
      report_path = paste0(basename, ".alignment.json"),
      width_in = width, height_in = height, python = python
    ), alignment_options)), error = function(error) {
      jsonlite::write_json(list(automated_status = "FAIL", stage = "alignment", error = conditionMessage(error)),
                           qa_path, auto_unbox = TRUE, pretty = TRUE)
      stop(error)
    })
  }
  draw_device <- function(open_device) {
    open_device()
    on.exit(grDevices::dev.off())
    draw(plot)
  }
  draw_device(function() grDevices::cairo_pdf(paste0(basename, ".pdf"), width = width, height = height, family = family))
  draw_device(function() svglite::svglite(paste0(basename, ".svg"), width = width, height = height))
  draw_device(function() ragg::agg_png(paste0(basename, ".png"), width = width, height = height, units = "in", res = dpi))
  if (tiff) draw_device(function() ragg::agg_tiff(paste0(basename, ".tiff"), width = width, height = height, units = "in", res = dpi))
  qa_path <- paste0(basename, ".qa.json")
  if (!nzchar(python)) {
    result <- list(automated_status = "NOT_AUDITABLE", unavailable_checks = "Python PDF QA runtime unavailable",
                   visual_review = list(status = "pending"))
    jsonlite::write_json(result, qa_path, auto_unbox = TRUE, pretty = TRUE)
    return(invisible(result))
  }
  args <- c(shQuote(file.path(.light_chart_dir, "publication.py")),
            shQuote(paste0(basename, ".pdf")), "--png", shQuote(paste0(basename, ".png")),
            "--width-mm", as.character(width_mm), "--height-mm", as.character(height_mm),
            "--normalize-cairo-page",
            "--min-font-pt", as.character(min_font_pt), "--json-out", shQuote(qa_path),
            "--extra-export", shQuote(paste0(basename, ".svg")))
  if (tiff) args <- c(args,"--extra-export",shQuote(paste0(basename,".tiff")))
  output <- suppressWarnings(system2(python, args, stdout = TRUE, stderr = TRUE))
  status <- attr(output, "status")
  if (length(output)) message(paste(output, collapse = "\n"))
  if (!file.exists(qa_path)) stop("Final PDF QA produced no report", call. = FALSE)
  result <- jsonlite::read_json(qa_path, simplifyVector = TRUE)
  result$project_style <- lc_project()
  result$resolved_fonts <- lc_fonts()
  result$minimum_font_pt <- min_font_pt
  if (!is.null(review_plots)) {
    result$figure_snapshot <- figure_snapshot_r(review_plots)
    result$mark_issues <- audit_marks_r(review_plots)
    if(length(result$mark_issues) && result$automated_status=='PASS')result$automated_status<-'REVIEW_REQUIRED'
  }
  if (!is.null(source_files)) {
    result$source_manifest <- source_manifest
    if (is.null(data_sources)) {
      # Preserve the old conservative all-inputs signature for existing callers.
      result$source_data_sha256 <- digest::digest(source_manifest,algo='sha256')
      result$source_data_scope <- 'all_source_files_legacy'
    } else {
      result$source_data_sha256 <- digest::digest(
        lapply(source_manifest[sort(data_sources)],function(entry) entry$sha256),algo='sha256')
      result$source_data_scope <- as.list(sort(data_sources))
    }
    current_sources <- tryCatch(source_manifest_r(source_files),error=function(e) NULL)
    if (!identical(source_manifest,current_sources)) {
      result$automated_status <- 'FAIL'
      result$failures <- c(result$failures,'Source files changed during export')
    }
  }
  jsonlite::write_json(result,qa_path,auto_unbox=TRUE,pretty=TRUE,null="null")
  if (!is.null(review_plots)) {
    color_status<-suppressWarnings(system2(python,c(shQuote(file.path(.light_chart_dir,'color_tools.py')),
      '--qa',shQuote(qa_path)),stdout=TRUE,stderr=TRUE))
    result<-jsonlite::read_json(qa_path,simplifyVector=FALSE)
    if(!is.null(attr(color_status,'status')) && attr(color_status,'status')!=0L)
      stop('Rendered group colors differ from the declared project mapping; inspect QA',call.=FALSE)
  }
  if (!is.null(status) && status != 0L) stop("Final figure checks failed or were unavailable; inspect the QA report", call. = FALSE)
  if (result$automated_status=='FAIL') stop("Source or figure checks failed; inspect the QA report",call.=FALSE)
  invisible(result)
}
