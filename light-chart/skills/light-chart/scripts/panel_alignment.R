# Render-time panel-alignment helper for R patchwork figures.
#
# Source this file from the selected R plotting script. It measures patchwork's
# final panel cells on a device with the same physical dimensions as the export,
# writes the backend-neutral JSON manifest consumed by audit_panel_alignment.py,
# and can run the blocking audit in one call.

.light_chart_alignment_dir <- local({
  source_paths <- vapply(sys.frames(), function(frame) {
    if (is.null(frame$ofile)) "" else as.character(frame$ofile)[1]
  }, character(1))
  candidates <- source_paths[basename(source_paths) == "panel_alignment.R"]
  if (!length(candidates)) stop("Load panel_alignment.R with source()", call. = FALSE)
  source_path <- tail(candidates, 1)
  dirname(normalizePath(source_path, mustWork = TRUE))
})

.nature_alignment_groups <- function(groups) {
  if (is.null(groups)) {
    return(NULL)
  }
  lapply(groups, function(group) as.character(unlist(group, use.names = FALSE)))
}

.nature_alignment_panel_rows <- function(grob) {
  rows <- grob$layout[grepl("^panel(?:-[0-9]+)?$", grob$layout$name, perl = TRUE), , drop = FALSE]
  if (nrow(rows) < 2) {
    stop("At least two patchwork panel cells are required for alignment QA", call. = FALSE)
  }
  rows[order(rows$t, rows$l), , drop = FALSE]
}

write_patchwork_panel_layout <- function(
  plot,
  manifest_path,
  width_in,
  height_in,
  panel_ids = NULL,
  row_groups = NULL,
  column_groups = NULL,
  exemptions = list(),
  design = NULL
) {
  for (package in c("patchwork", "grid", "jsonlite")) {
    if (!requireNamespace(package, quietly = TRUE)) {
      stop(sprintf("Package '%s' is required for patchwork alignment QA", package), call. = FALSE)
    }
  }
  if (!is.numeric(width_in) || length(width_in) != 1 || !is.finite(width_in) || width_in <= 0 ||
      !is.numeric(height_in) || length(height_in) != 1 || !is.finite(height_in) || height_in <= 0) {
    stop("width_in and height_in must be positive finite numbers", call. = FALSE)
  }

  # Null gtable units only resolve inside the rendered viewport. Measuring raw
  # grob$widths would report zero panel sizes. Use actual device coordinates.
  probe_path <- tempfile(fileext = ".pdf")
  grDevices::cairo_pdf(probe_path, width = width_in, height = height_in)
  device_open <- TRUE
  on.exit({
    if (device_open) grDevices::dev.off()
    unlink(probe_path)
  }, add = TRUE)
  grob <- if(inherits(plot,'patchwork'))patchwork::patchworkGrob(plot) else ggplot2::ggplotGrob(plot)
  grid::grid.newpage()
  grid::grid.draw(grob)
  grid::grid.force()
  listing <- grid::grid.ls(viewports = TRUE, grobs = FALSE, print = FALSE)
  selected <- which(grepl("^panel(?:-[0-9]+)*\\.", listing$name, perl = TRUE))
  paths <- paste(listing$vpPath[selected], listing$name[selected], sep = "::")
  selected <- selected[!duplicated(paths)]
  if (length(selected) < 2) stop("At least two rendered patchwork panels are required", call. = FALSE)
  if (is.null(panel_ids)) panel_ids <- letters[seq_along(selected)]
  panel_ids <- as.character(panel_ids)
  if (length(panel_ids) != length(selected) || anyNA(panel_ids) || anyDuplicated(panel_ids) || any(!nzchar(panel_ids))) {
    stop("panel_ids must be unique and match the rendered panels", call. = FALSE)
  }
  parents <- unique(listing$vpPath[selected])
  if (is.null(design) && length(parents) > 1 && is.null(row_groups) && is.null(column_groups)) {
    stop("Nested patchwork needs an explicit design matrix or comparable row/column groups", call. = FALSE)
  }
  if (!is.null(design)) {
    design <- as.matrix(design)
    if (!setequal(as.character(design[!is.na(design)]), panel_ids)) {
      stop("design must contain exactly the declared panel IDs (NA for blanks)", call. = FALSE)
    }
  }
  panels <- lapply(seq_along(selected), function(index) {
    entry <- selected[index]
    components <- c(strsplit(listing$vpPath[entry], "::", fixed = TRUE)[[1]], listing$name[entry])
    components <- components[components != "ROOT" & nzchar(components)]
    grid::upViewport(0)
    grid::downViewport(do.call(grid::vpPath, as.list(components)))
    lower <- grid::deviceLoc(grid::unit(0, "npc"), grid::unit(0, "npc"), valueOnly = TRUE)
    upper <- grid::deviceLoc(grid::unit(1, "npc"), grid::unit(1, "npc"), valueOnly = TRUE)
    # Cairo's fractional page correction preserves the top-left origin.
    y_shift <- height_in * 72 - grDevices::dev.size("in")[[2]] * 72
    panel <- list(id = panel_ids[index],
                  bbox_pt = unname(c(lower$x*72, lower$y*72+y_shift, upper$x*72, upper$y*72+y_shift)))
    if (!is.null(design)) {
      cells <- which(design == panel_ids[index], arr.ind = TRUE)
      if (nrow(cells) != (max(cells[,1])-min(cells[,1])+1)*(max(cells[,2])-min(cells[,2])+1)) {
        stop("Each design panel must occupy a rectangle", call. = FALSE)
      }
      panel$grid_id <- "declared-patchwork-design"
      panel$row_start <- min(cells[,1])-1L; panel$row_stop <- max(cells[,1])
      panel$col_start <- min(cells[,2])-1L; panel$col_stop <- max(cells[,2])
    } else {
      coordinates <- as.integer(strsplit(sub("^.*\\.", "", listing$name[entry]), "-", fixed = TRUE)[[1]])
      panel$grid_id <- listing$vpPath[entry]
      panel$row_start <- coordinates[1]-1L; panel$row_stop <- coordinates[3]
      panel$col_start <- coordinates[2]-1L; panel$col_stop <- coordinates[4]
    }
    panel
  })
  grid::upViewport(0)

  manifest <- list(
    schema_version = 1L,
    backend = "r-patchwork",
    figure = list(width_pt = width_in * 72, height_pt = height_in * 72),
    panels = panels,
    exemptions = exemptions,
    design = design
  )
  normalized_rows <- .nature_alignment_groups(row_groups)
  normalized_columns <- .nature_alignment_groups(column_groups)
  if (!is.null(normalized_rows)) {
    manifest$row_groups <- normalized_rows
  }
  if (!is.null(normalized_columns)) {
    manifest$column_groups <- normalized_columns
  }

  dir.create(dirname(manifest_path), recursive = TRUE, showWarnings = FALSE)
  temporary_path <- tempfile(pattern = ".panel-layout-", tmpdir = dirname(manifest_path), fileext = ".json")
  jsonlite::write_json(manifest, temporary_path, auto_unbox = TRUE, pretty = TRUE, digits = NA)
  if (!file.rename(temporary_path, manifest_path)) {
    unlink(temporary_path)
    stop("Could not activate the patchwork alignment manifest atomically", call. = FALSE)
  }

  grDevices::dev.off()
  device_open <- FALSE
  unlink(probe_path)
  invisible(manifest)
}

require_patchwork_panel_alignment <- function(
  plot,
  manifest_path,
  report_path,
  width_in,
  height_in,
  panel_ids = NULL,
  row_groups = NULL,
  column_groups = NULL,
  exemptions = list(),
  design = NULL,
  audit_script = file.path(.light_chart_alignment_dir, "audit_panel_alignment.py"),
  python = Sys.which("python"),
  overlay_svg = NULL,
  tolerance_pt = 1.5,
  gutter_tolerance_pt = 1.5,
  strict = TRUE
) {
  if (!nzchar(python)) {
    stop("Python is required for the backend-neutral panel-alignment JSON audit", call. = FALSE)
  }
  if (!file.exists(audit_script)) {
    stop(sprintf("Panel-alignment audit script not found: %s", audit_script), call. = FALSE)
  }
  write_patchwork_panel_layout(
    plot = plot,
    manifest_path = manifest_path,
    width_in = width_in,
    height_in = height_in,
    panel_ids = panel_ids,
    row_groups = row_groups,
    column_groups = column_groups,
    exemptions = exemptions,
    design = design
  )

  args <- c(
    shQuote(audit_script),
    shQuote(manifest_path),
    "--json-out", shQuote(report_path),
    "--tolerance-pt", format(tolerance_pt, scientific = FALSE),
    "--gutter-tolerance-pt", format(gutter_tolerance_pt, scientific = FALSE)
  )
  if (!is.null(overlay_svg)) {
    args <- c(args, "--overlay-svg", shQuote(overlay_svg))
  }
  if (isTRUE(strict)) {
    args <- c(args, "--strict")
  }
  output <- suppressWarnings(system2(python, args = args, stdout = TRUE, stderr = TRUE))
  status <- attr(output, "status")
  if (is.null(status)) {
    status <- 0L
  }
  if (length(output)) {
    message(paste(output, collapse = "\n"))
  }
  if (status != 0L) {
    stop(
      sprintf("Panel alignment gate failed with exit code %d; inspect %s", status, report_path),
      call. = FALSE
    )
  }
  invisible(jsonlite::read_json(report_path, simplifyVector = TRUE))
}
