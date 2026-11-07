# Native R domain plots. Sources: nature R workflow; ordinary annotated-heatmap
# structures. Data, tests and significance are never fabricated by these helpers.

.lc_require <- function(packages) {
  for (p in packages) if (!requireNamespace(p, quietly = TRUE))
    stop(sprintf("Missing R package: %s", p), call. = FALSE)
}

annotated_heatmap_r <- function(matrix, sample_metadata, sample_id, annotation_cols,
                                 annotation_colors, limits, center = NULL,
                                 cluster_rows = FALSE, cluster_columns = FALSE,
                                 row_split = NULL, column_split = NULL,
                                 name = "Value", na_col = NULL,
                                 font_family = NULL, font_size = NULL,
                                 show_column_names = FALSE) {
  .lc_require(c("ComplexHeatmap", "circlize"))
  if(is.null(font_family)) font_family <- if(exists('lc_fonts')) lc_fonts()$latin else "sans"
  if(is.null(font_size)) font_size <- if(exists('lc_project')) lc_project()$typography$base_pt else 7
  if(is.null(na_col)) na_col <- if(exists('lc_color')) lc_color('missing') else '#D9DEE3'
  # ComplexHeatmap internally measures on pdf(NULL), which only knows generic
  # PostScript families. Use the corresponding generic for these standard faces;
  # final Cairo/ragg devices resolve sans/serif natively, checked in the PDF.
  if(font_family %in% c('Arial','Helvetica','DejaVu Sans','Liberation Sans')) font_family <- 'sans'
  if(font_family %in% c('Times New Roman','Times','DejaVu Serif','Liberation Serif')) font_family <- 'serif'
  if (!is.matrix(matrix) || !is.numeric(matrix) || any(dim(matrix) < 1L) ||
      is.null(rownames(matrix)) || is.null(colnames(matrix)))
    stop("matrix needs numeric values, row names and sample column names", call. = FALSE)
  if (anyDuplicated(rownames(matrix)) || anyDuplicated(colnames(matrix)))
    stop("Matrix row and column names must be unique", call. = FALSE)
  if (any(is.infinite(matrix))) stop("Infinite values are not supported", call. = FALSE)
  if (length(limits) != 2L || any(!is.finite(limits)) || limits[1] >= limits[2])
    stop("Explicit increasing finite limits are required", call. = FALSE)
  observed <- matrix[is.finite(matrix)]
  if (!length(observed) || any(observed < limits[1] | observed > limits[2]))
    stop("No observations, or values fall outside the declared color limits", call. = FALSE)
  required <- c(sample_id, annotation_cols)
  if (!all(required %in% names(sample_metadata)))
    stop("Metadata is missing requested fields", call. = FALSE)
  ids <- as.character(sample_metadata[[sample_id]])
  if (anyNA(ids) || anyDuplicated(ids) || !setequal(ids, colnames(matrix)))
    stop("Metadata and matrix sample IDs must match exactly and uniquely", call. = FALSE)
  metadata <- sample_metadata[match(colnames(matrix), ids), annotation_cols, drop = FALSE]
  if (anyNA(metadata)) stop("Declare how missing metadata should be encoded before plotting", call. = FALSE)
  if (!setequal(names(annotation_colors), annotation_cols))
    stop("Provide one named categorical palette for each annotation", call. = FALSE)
  for (col in annotation_cols) {
    values <- as.character(metadata[[col]])
    if (!all(unique(values) %in% names(annotation_colors[[col]])))
      stop(sprintf("Incomplete palette for %s", col), call. = FALSE)
    metadata[[col]] <- values
  }
  if ((!is.null(row_split) && length(row_split) != nrow(matrix)) ||
      (!is.null(column_split) && length(column_split) != ncol(matrix)))
    stop("Split vectors must match matrix order and dimensions", call. = FALSE)
  if ((cluster_rows || cluster_columns) && anyNA(matrix))
    stop("Clustering missing values requires an explicit distance/imputation policy", call. = FALSE)
  # Deliberately do not calculate z scores, filter genes, impute or add stars.
  if (is.null(center)) {
    cols <- if(exists('lc_project')) lc_project()$palettes$sequential else c("#F1F5F8", "#174B75")
    color_fn <- circlize::colorRamp2(seq(limits[1],limits[2],length.out=length(cols)),cols,space="sRGB")
  } else {
    if (length(center) != 1 || !is.finite(center) || center <= limits[1] || center >= limits[2])
      stop("center must lie strictly inside limits", call. = FALSE)
    cols <- if(exists('lc_project')) lc_project()$palettes$diverging else c("#356C99", "#FAFAF7", "#B85D50")
    color_fn <- circlize::colorRamp2(c(limits[1], center, limits[2]),cols,space="sRGB")
  }
  top <- ComplexHeatmap::HeatmapAnnotation(
    df = metadata, col = annotation_colors,
    simple_anno_size = grid::unit(2.2, "mm"),
    annotation_name_gp = grid::gpar(fontfamily = font_family, fontsize = font_size),
    annotation_legend_param = lapply(annotation_cols, function(x) list(
      title_gp = grid::gpar(fontfamily = font_family, fontsize = font_size),
      labels_gp = grid::gpar(fontfamily = font_family, fontsize = font_size)))
  )
  ComplexHeatmap::Heatmap(matrix, name = name, col = color_fn, na_col = na_col,
    cluster_rows = cluster_rows, cluster_columns = cluster_columns,
    clustering_distance_rows = "euclidean", clustering_distance_columns = "euclidean",
    clustering_method_rows = "complete", clustering_method_columns = "complete",
    row_split = row_split, column_split = column_split, cluster_row_slices = FALSE,
    cluster_column_slices = FALSE, top_annotation = top,
    show_column_names = show_column_names, row_names_side = "left",
    row_names_gp = grid::gpar(fontfamily = font_family, fontsize = font_size),
    column_names_gp = grid::gpar(fontfamily = font_family, fontsize = font_size),
    column_title_gp = grid::gpar(fontfamily = font_family, fontsize = font_size + 1),
    row_title_gp = grid::gpar(fontfamily = font_family, fontsize = font_size + 1),
    rect_gp = grid::gpar(col = NA), border = FALSE,
    heatmap_legend_param = list(title_gp = grid::gpar(fontfamily = font_family, fontsize = font_size),
      labels_gp = grid::gpar(fontfamily = font_family, fontsize = font_size)))
}

survival_panel_r <- function(data, time, event, group, id, risk_times,
                             palette, time_label, group_order = NULL,
                             conf_level = 0.95, show_ci = TRUE,
                             font_family = NULL, font_size = NULL) {
  .lc_require(c("survival", "ggplot2", "patchwork"))
  if(is.null(font_family)) font_family <- if(exists('lc_fonts')) lc_fonts()$latin else "sans"
  if(is.null(font_size)) font_size <- if(exists('lc_project')) lc_project()$typography$base_pt else 8
  if (!all(c(time,event,group,id) %in% names(data))) stop("Missing requested columns", call. = FALSE)
  d <- data.frame(time = data[[time]], event = data[[event]],
                  group = as.character(data[[group]]), id = as.character(data[[id]]))
  if (!nrow(d) || anyNA(d) || anyDuplicated(d$id))
    stop("Use one complete row per independent subject; no silent exclusion", call. = FALSE)
  if (!is.numeric(d$time) || any(!is.finite(d$time)) || any(d$time < 0) ||
      !is.numeric(d$event) || !all(d$event %in% c(0,1)))
    stop("Time must be finite/nonnegative; event must explicitly be 0=censored, 1=event", call. = FALSE)
  if (is.null(group_order)) group_order <- unique(d$group)
  if (anyDuplicated(group_order) || !setequal(group_order, unique(d$group)) ||
      !all(group_order %in% names(palette))) stop("Invalid group order or incomplete palette", call. = FALSE)
  if (!is.numeric(risk_times) || !length(risk_times) || any(!is.finite(risk_times)) ||
      any(diff(risk_times) <= 0) || risk_times[1] != 0)
    stop("risk_times must increase strictly from 0", call. = FALSE)
  plot_range <- c(0,max(risk_times,d$time)) # Risk ticks must never truncate follow-up.
  if (!is.numeric(conf_level) || length(conf_level)!=1 || !is.finite(conf_level) ||
      conf_level <= 0 || conf_level >= 1) stop("Invalid confidence level", call. = FALSE)
  d$group <- factor(d$group, levels = group_order)
  fit <- survival::survfit(survival::Surv(time, event) ~ group, data = d,
                           conf.int = conf_level, conf.type = "log-log")
  counts <- if (is.null(fit$strata)) length(fit$time) else as.integer(fit$strata)
  curve <- data.frame(time = fit$time, survival = fit$surv,
                      lower = fit$lower, upper = fit$upper,
                      censored = fit$n.censor, group = rep(group_order, counts))
  starts <- data.frame(time = 0, survival = 1, lower = 1, upper = 1,
                       censored = 0, group = group_order)
  curve <- rbind(starts, curve)
  curve <- curve[order(match(curve$group, group_order), curve$time),]
  # survfit returns the KM estimates / log-log Greenwood limits. Expand to
  # step coordinates before geom_ribbon, so its band does not imply linear KM.
  # Explicitly use previous value followed by current value at each event time.
  stepped <- do.call(rbind, lapply(group_order, function(g) {
    z <- curve[curve$group == g,]
    ix <- rep(seq_len(nrow(z)), each=2)[-2*nrow(z)]
    out <- z[ix,,drop=FALSE]
    out$time <- c(0, rep(z$time[-1], each=2))
    out
  }))
  theme <- ggplot2::theme_classic(base_size = font_size, base_family = font_family) +
    ggplot2::theme(axis.line = ggplot2::element_line(linewidth = .3),
      axis.text = ggplot2::element_text(size=font_size),
      legend.text = ggplot2::element_text(size=font_size),
      axis.ticks = ggplot2::element_line(linewidth = .3),
      legend.position = "top", legend.title = ggplot2::element_blank(),
      plot.margin = ggplot2::margin(4,8,4,4))
  p <- ggplot2::ggplot(curve, ggplot2::aes(time, survival, color = group, group=group))
  if (show_ci) p <- p + ggplot2::geom_ribbon(data=stepped,
    ggplot2::aes(ymin=lower, ymax=upper, fill=group), color=NA, alpha=.12, show.legend=FALSE)
  p <- p + ggplot2::geom_step(linewidth=.7, direction="hv") +
    ggplot2::geom_point(data=curve[curve$censored>0,], shape=3, size=1.5, stroke=.4, show.legend=FALSE) +
    ggplot2::scale_color_manual(values=palette, limits=group_order) +
    ggplot2::scale_fill_manual(values=palette, limits=group_order) +
    ggplot2::scale_x_continuous(breaks=risk_times, limits=plot_range, expand=c(.03,0)) +
    ggplot2::scale_y_continuous(breaks=seq(0,1,.25), limits=c(0,1), expand=c(.015,0)) +
    ggplot2::labs(x=NULL,y="Survival probability") + theme +
    ggplot2::theme(axis.text.x=ggplot2::element_blank(),axis.ticks.x=ggplot2::element_blank())
  risk <- expand.grid(time=risk_times,group=group_order,KEEP.OUT.ATTRS=FALSE,stringsAsFactors=FALSE)
  risk$n <- vapply(seq_len(nrow(risk)), function(i)
    sum(d$group==risk$group[i] & d$time>=risk$time[i]), integer(1))
  risk$group <- factor(risk$group, levels=rev(group_order))
  r <- ggplot2::ggplot(risk,ggplot2::aes(time,group,label=n,color=group)) +
    ggplot2::geom_text(size=font_size*25.4/72.27, family=font_family, show.legend=FALSE) +
    ggplot2::scale_color_manual(values=palette) +
    ggplot2::scale_x_continuous(breaks=risk_times,limits=plot_range,expand=c(.03,0)) +
    ggplot2::labs(x=time_label,y=NULL,title="Number at risk") + theme +
    ggplot2::theme(axis.line.y=ggplot2::element_blank(),axis.ticks.y=ggplot2::element_blank(),
      plot.title=ggplot2::element_text(size=font_size,face="plain"))
  list(plot=patchwork::wrap_plots(p,r,ncol=1,heights=c(4,1.2)),fit=fit,
       curve=curve,risk=risk,n=nrow(d),events=sum(d$event),
       definitions=list(event="1=event; 0=censored",at_risk="Time >= tick, immediately before any event/censoring at that tick",
         confidence=paste0(conf_level*100,"% log-log Greenwood confidence interval from survival::survfit")))
}
