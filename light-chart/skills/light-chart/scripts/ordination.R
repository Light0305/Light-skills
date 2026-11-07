# Native R ecological ordination with explicit identity and transformation.
# Hellinger: vegan::decostand documentation, sqrt(x / rowSums(x)).
# PCA: stats::prcomp documentation; centre=TRUE, scale.=FALSE, no silent na.omit.
# Nature evidence architecture and f4 composition matrices inform the separation
# of projection, environmental association and complete original feature matrix.

hellinger_pca_r <- function(data, metadata, id, values, value_semantics,
                             metadata_fields = character()) {
  if (!is.data.frame(data) || !is.data.frame(metadata) || !nrow(data) ||
      !id %in% names(data) || !id %in% names(metadata)) stop('Nonempty tables and ID field required')
  if (length(values) < 2L || anyDuplicated(values) || !all(values %in% names(data)) ||
      !all(vapply(data[values],function(v)is.numeric(v)&&!is.complex(v),logical(1)))) stop('Unique real numeric matrix fields required')
  if (length(value_semantics)!=1L || !nzchar(value_semantics)) stop('Declare original value semantics')
  ids <- as.character(data[[id]]); mids <- as.character(metadata[[id]])
  if (anyNA(ids) || anyNA(mids) || any(!nzchar(ids)) || any(!nzchar(mids)) ||
      anyDuplicated(ids) || anyDuplicated(mids) || !setequal(ids,mids))
    stop('Data and metadata IDs must match exactly and uniquely')
  if (!all(metadata_fields %in% names(metadata))) stop('Missing requested metadata fields')
  aligned <- metadata[match(ids,mids),,drop=FALSE]
  if (anyNA(aligned[metadata_fields])) stop('Resolve missing requested metadata explicitly')
  mat <- as.matrix(data[values]); rownames(mat)<-ids
  if (any(!is.finite(mat)) || any(mat<0) || any(rowSums(mat)<=0))
    stop('Finite nonnegative values and strictly positive site totals required')
  transformed <- sqrt(mat/rowSums(mat))
  fit <- stats::prcomp(transformed,center=TRUE,scale.=FALSE)
  variance <- fit$sdev^2/sum(fit$sdev^2)
  if (length(variance)<2L || !is.finite(variance[2]) || variance[2]<1e-12)
    stop('At least two nonzero PCA dimensions required')
  # Sign orientation is arbitrary in PCA. Fix each component by its largest
  # absolute loading, preserving distances and allowing cross-backend checking.
  for (j in seq_len(ncol(fit$rotation))) {
    anchor <- which.max(abs(fit$rotation[,j]))
    if(fit$rotation[anchor,j]<0) {
      fit$rotation[,j]<- -fit$rotation[,j];fit$x[,j]<- -fit$x[,j]
    }
  }
  scores <- data.frame(.id=ids,PC1=fit$x[,1],PC2=fit$x[,2],stringsAsFactors=FALSE)
  names(scores)[1]<-id
  scores <- cbind(scores,aligned[setdiff(names(aligned),id)])
  list(scores=scores,loadings=fit$rotation,variance=variance,original=mat,
       transformed=transformed,metadata=aligned,
       parameters=list(transform='sqrt(value / site total)',center=TRUE,scale=FALSE,
         distance='Euclidean on Hellinger-transformed values',value_semantics=value_semantics,
         samples=nrow(mat),features=ncol(mat),implicit_exclusion=FALSE,
         axis_sign='largest absolute loading is positive; arbitrary sign has no inferential meaning'))
}

ordination_plot_r <- function(result, id, group, palette=NULL, shapes,
                               group_order=if(is.null(palette))names(shapes) else names(palette), label_sites=TRUE, font_size=7.5,
                               font_family=NULL,label_max_iter=40000L,label_verbose=FALSE,
                               label_box_padding_mm=1.4,label_point_padding_mm=0,
                               label_force=2,label_force_pull=.7,
                               color_by=NULL,color_limits=NULL,color_colors=NULL,color_label=NULL) {
  if(!requireNamespace('ggplot2',quietly=TRUE))stop('ggplot2 required')
  if(is.null(font_family)) {
    font_family<-if(exists('light_chart_family',mode='function'))light_chart_family('en') else
      if(exists('lc_fonts',mode='function'))lc_fonts()$latin else 'sans'
  }
  if(length(font_family)!=1L || !is.character(font_family) || !nzchar(font_family))
    stop('A resolved font family is required')
  if(label_sites && !requireNamespace('ggrepel',quietly=TRUE))
    stop('ggrepel is required for labelled ordination; explicitly disable site labels only when identities are not needed by the scientific task')
  if(length(label_max_iter)!=1L || !is.finite(label_max_iter) || label_max_iter<1 || label_max_iter!=as.integer(label_max_iter))
    stop('Declare a positive finite label iteration budget')
  controls<-c(font_size,label_box_padding_mm,label_point_padding_mm,label_force,label_force_pull)
  if(length(controls)!=5L || any(!is.finite(controls)) || font_size<=0 ||
     label_box_padding_mm<0 || label_point_padding_mm<0 || label_force<=0 || label_force_pull<=0)
    stop('Font size and label forces must be positive; physical label padding must be nonnegative')
  d<-result$scores
  if(!is.data.frame(d) || !nrow(d) || !all(c(id,group,'PC1','PC2')%in%names(d)) ||
     !all(vapply(d[c('PC1','PC2')],function(v)is.numeric(v)&&!is.complex(v)&&all(is.finite(v)),logical(1))) ||
     length(result$variance)<2 || any(!is.finite(result$variance)) || any(result$variance<0) ||
     sum(result$variance)>1+1e-9)stop('Finite real PCA scores and explained variance fractions required')
  if(anyNA(d[[group]]) || anyDuplicated(group_order) ||
     !all(unique(as.character(d[[group]]))%in%group_order) ||
     !all(group_order%in%names(shapes)))stop('Explicit group identity/shape mapping required')
  if(is.null(color_by)) {
    if(!all(group_order%in%names(palette)))stop('Explicit categorical group colors required')
    if(!is.null(color_limits) || !is.null(color_colors) || !is.null(color_label))
      stop('Declare color_by for continuous metadata color options')
    tryCatch(grDevices::col2rgb(palette),error=function(e)stop('Invalid categorical colors'))
  } else {
    if(!is.character(color_by) || length(color_by)!=1L || !color_by%in%names(d) ||
       !is.numeric(d[[color_by]]) || is.complex(d[[color_by]]) || any(!is.finite(d[[color_by]])))
      stop('color_by must name finite real numeric metadata in the identity-aligned scores')
    if(is.null(color_limits))color_limits<-range(d[[color_by]])
    if(!is.numeric(color_limits) || is.complex(color_limits) || length(color_limits)!=2L ||
       any(!is.finite(color_limits)) || color_limits[1]>=color_limits[2] ||
       min(d[[color_by]])<color_limits[1] || max(d[[color_by]])>color_limits[2])
      stop('Continuous color limits must increase and cover every value without clipping; constant metadata needs explicit limits')
    if(is.null(color_colors))color_colors<-if(exists('lc_project',mode='function'))
      lc_project()$palettes$sequential else c('#F3F8F7','#C0DDD5','#2B776D')
    if(!is.character(color_colors) || length(color_colors)<2L || anyNA(color_colors))
      stop('At least two explicit continuous colors required')
    tryCatch(grDevices::col2rgb(color_colors),error=function(e)stop('Invalid continuous colors'))
    if(is.null(color_label))color_label<-color_by
    if(!is.character(color_label) || length(color_label)!=1L || is.na(color_label) || !nzchar(color_label))
      stop('A continuous colorbar label is required')
  }
  if(anyNA(d[[id]]) || any(!nzchar(as.character(d[[id]]))) || anyDuplicated(d[[id]]))
    stop('Labelled sites require unique nonmissing identities')
  # A fixed ID order makes the stochastic solver invariant to input row shuffle.
  # This changes draw order only; scores and their identities stay untouched.
  d<-d[order(as.character(d[[id]]),method='radix'),,drop=FALSE]
  d$.group<-factor(d[[group]],levels=group_order)
  if(is.null(color_by)) {
    p<-ggplot2::ggplot(d,ggplot2::aes(PC1,PC2,color=.group,shape=.group))+
      ggplot2::scale_color_manual(values=palette,limits=group_order)
  } else {
    d$.continuous_color<-d[[color_by]]
    p<-ggplot2::ggplot(d,ggplot2::aes(PC1,PC2,color=.continuous_color,shape=.group))+
      ggplot2::scale_color_gradientn(colours=color_colors,limits=color_limits,name=color_label,
        space='Lab',guide=ggplot2::guide_colorbar(order=1,
          barwidth=grid::unit(22,'mm'),barheight=grid::unit(2.2,'mm')))
  }
  p<-p+ggplot2::scale_shape_manual(values=shapes,limits=group_order)+
    ggplot2::labs(x=sprintf('PC1 (%.1f%%)',100*result$variance[1]),
                 y=sprintf('PC2 (%.1f%%)',100*result$variance[2]),
                 color=if(is.null(color_by))NULL else color_label,
                 shape=if(is.null(color_by))NULL else group)+
    ggplot2::coord_equal(clip='off')+
    ggplot2::theme_classic(base_size=font_size,base_family=font_family)+
    ggplot2::theme(axis.text=ggplot2::element_text(size=font_size,color='#22262B'),
      legend.text=ggplot2::element_text(size=font_size),
      legend.title=ggplot2::element_text(size=font_size),
      legend.position='top',legend.key.width=grid::unit(3,'mm'),
      legend.spacing.x=grid::unit(1,'mm'),plot.margin=ggplot2::margin(4,6,4,4))
  if(label_sites) {
    p<-p+ggrepel::geom_text_repel(ggplot2::aes(label=.data[[id]]),color='#22262B',family=font_family,
        size=font_size/ggplot2::.pt,point.size=1,
        box.padding=grid::unit(label_box_padding_mm,'mm'),
        point.padding=grid::unit(label_point_padding_mm,'mm'),
        min.segment.length=0,segment.color='#6C737A',segment.size=.2,seed=20261026,
        max.overlaps=Inf,max.time=Inf,max.iter=as.integer(label_max_iter),
        force=label_force,force_pull=label_force_pull,verbose=label_verbose,show.legend=FALSE)
  }
  # Draw the actual markers over leaders. ggrepel's circular connector anchor
  # lies inside all four conventional filled marker shapes at size 2.1; the
  # painted marker itself trims each leader to its real boundary. In particular
  # a triangle no longer receives a floating circular endpoint plus line padding.
  # Repulsion still uses real device font metrics, all IDs, and the exact scores.
  p+ggplot2::geom_point(size=2.1,stroke=.45)
}

# Read real, already-drawn ggrepel text and connector geometry in physical mm.
# Call after the final-size native R draw, before closing that graphics device.
# No substitute font, text-length estimate, or coordinate jitter is used.
ordination_label_geometry_r <- function() {
  grid::grid.force()
  listing<-grid::grid.ls(print=FALSE)
  trees<-which(grepl('^geom_text_repel[.]textrepeltree',listing$name))
  reports<-list()
  on.exit(grid::upViewport(0),add=TRUE)
  for(t in trees) {
    path<-paste(listing$gPath[t],listing$name[t],sep='::')
    tree<-grid::grid.get(path)
    parts<-strsplit(listing$gPath[t],'::',fixed=TRUE)[[1]]
    cells<-parts[grepl('^panel(-[0-9]+)?[.][0-9]+-',parts)]
    if(!length(cells))stop('Cannot resolve the native ordination panel viewport')
    grid::seekViewport(cells[length(cells)])
    width<-grid::convertWidth(grid::unit(1,'npc'),'mm',valueOnly=TRUE)
    height<-grid::convertHeight(grid::unit(1,'npc'),'mm',valueOnly=TRUE)
    # Use the actual drawn marker grob, including ggplot's pointsize/stroke
    # gpar. grobCoords applies that gpar; grobPoints alone does not.
    # Native public coordinate API: R gridCoords documentation and R grid
    # grobCoords.points; symbol geometry: src/main/engine.c, GESymbol.
    # https://stat.ethz.ch/R-manual/R-devel/library/grid/html/gridCoords.html
    point_index<-which(grepl('^geom_point[.]points',listing$name) &
      listing$gPath==listing$gPath[t])
    marker<-marker_coords<-NULL
    if(length(point_index)==1L) {
      marker<-grid::grid.get(paste(listing$gPath[point_index],listing$name[point_index],sep='::'))
      if(length(marker$x)!=length(tree$lab) || any(!marker$pch%in%c(15,16,17,18)))
        marker<-NULL
      if(!is.null(marker))marker_coords<-grid::grobCoords(marker,closed=TRUE)
    }
    rows<-list()
    for(i in seq_along(tree$lab)) {
      text<-tree$children[[paste0('textrepelgrob',i)]]
      if(is.null(text))stop('A required ordination label was not drawn')
      xy<-function(x,y)c(grid::convertX(x,'mm',valueOnly=TRUE),grid::convertY(y,'mm',valueOnly=TRUE))
      point<-xy(grid::unit(tree$data$x[i],'native'),grid::unit(tree$data$y[i],'native'))
      label<-xy(text$x,text$y)
      connector<-tree$children[[paste0('segmentrepelgrob',i)]]
      start<-end<-c(NA_real_,NA_real_)
      if(!is.null(connector)) {
        segment<-connector$children$segment
        if(is.null(segment))stop('Expected a straight native ordination connector')
        start<-xy(segment$x0,segment$y0);end<-xy(segment$x1,segment$y1)
      }
      rows[[i]]<-data.frame(label=as.character(tree$lab[i]),point_x_mm=point[1],point_y_mm=point[2],
        text_x_mm=label[1],text_y_mm=label[2],
        left_mm=grid::convertX(grid::grobX(text,'west'),'mm',valueOnly=TRUE),
        right_mm=grid::convertX(grid::grobX(text,'east'),'mm',valueOnly=TRUE),
        bottom_mm=grid::convertY(grid::grobY(text,'south'),'mm',valueOnly=TRUE),
        top_mm=grid::convertY(grid::grobY(text,'north'),'mm',valueOnly=TRUE),
        font_size_pt=text$gp$fontsize,font_family=text$gp$fontfamily,
        connector=!is.null(connector),label_end_x_mm=start[1],label_end_y_mm=start[2],
        point_end_x_mm=end[1],point_end_y_mm=end[2],
        inner_anchor_distance_mm=sqrt(sum((end-point)^2)),stringsAsFactors=FALSE)
      if(!is.null(marker_coords)) {
        coords<-marker_coords[[i]]
        if(max(abs(xy(marker$x[i],marker$y[i])-point))>1e-7)
          stop('Native marker order does not match measured label identities; remeasure an identity-aligned ordination layer')
        # grobCoords returns inches in the current panel, not device-global
        # coordinates. Match the same local origin as the measured centres.
        origin<-list(x=point[1]/25.4,y=point[2]/25.4)
        if(!length(coords$x) || !length(coords$y))stop('A native filled-marker outline is unavailable')
        # Conservative axis-aligned envelope, not exact shape intersection.
        # Outward 0.01 mm covers circle-outline sampling and vector rounding.
        # Shapes15:18 are native filled symbols: their stroke contribution is
        # already incorporated by ggplot into this actually drawn point grob.
        rows[[i]]$marker_left_mm<-point[1]+(min(coords$x)-origin$x)*25.4-.01
        rows[[i]]$marker_right_mm<-point[1]+(max(coords$x)-origin$x)*25.4+.01
        rows[[i]]$marker_bottom_mm<-point[2]+(min(coords$y)-origin$y)*25.4-.01
        rows[[i]]$marker_top_mm<-point[2]+(max(coords$y)-origin$y)*25.4+.01
        rows[[i]]$marker_radius_mm<-max(sqrt((coords$x-origin$x)^2+(coords$y-origin$y)^2))*25.4+.01
        rows[[i]]$marker_shape<-rep_len(marker$pch,length(tree$lab))[i]
        rows[[i]]$marker_fontsize_pt<-rep_len(marker$gp$fontsize,length(tree$lab))[i]
        rows[[i]]$marker_lwd<-rep_len(marker$gp$lwd,length(tree$lab))[i]
      }
    }
    reports[[length(reports)+1L]]<-list(panel_viewport=cells[length(cells)],
      width_mm=width,height_mm=height,sites=do.call(rbind,rows),
      marker_footprint_method=if(is.null(marker_coords))'unavailable' else
        'Native grid::grobCoords filled-pch15:18 outline with actual gpar; conservative axis-aligned envelope plus0.01mm outward margin, not exact shape intersection')
    grid::upViewport(0)
  }
  reports
}

# Detect unresolved physical marker clusters from measured final-device geometry.
# A connected component, rather than a selected site ID, defines a zoom region.
ordination_overlap_clusters_r <- function(geometry,marker_diameter_mm=2.1) {
  sites<-geometry$sites
  if(!is.data.frame(sites) || !all(c('label','point_x_mm','point_y_mm')%in%names(sites)) ||
     anyDuplicated(sites$label) || anyNA(sites$label) ||
     any(!is.finite(as.matrix(sites[c('point_x_mm','point_y_mm')]))))
    stop('Measured physical positions, unique IDs and a positive marker diameter are required')
  if(!is.null(marker_diameter_mm) && (length(marker_diameter_mm)!=1 ||
     !is.finite(marker_diameter_mm) || marker_diameter_mm<=0))
    stop('A positive finite explicit circular marker diameter is required')
  n<-nrow(sites);if(n<2)return(list())
  distances<-as.matrix(stats::dist(sites[c('point_x_mm','point_y_mm')]))
  if(is.null(marker_diameter_mm)) {
    # NULL explicitly selects measured envelopes instead of the legacy caller-
    # supplied circular diameter. Envelope contact means possible overlap only.
    fields<-c('marker_left_mm','marker_right_mm','marker_bottom_mm','marker_top_mm')
    if(!all(fields%in%names(sites)) || any(!is.finite(as.matrix(sites[fields]))) ||
       any(sites$marker_left_mm>=sites$marker_right_mm) ||
       any(sites$marker_bottom_mm>=sites$marker_top_mm))
      stop('Measure supported native filled-marker footprints before checking envelope overlap')
    x<-outer(sites$marker_left_mm,sites$marker_right_mm,'<=')
    y<-outer(sites$marker_bottom_mm,sites$marker_top_mm,'<=')
    adjacency<-x & t(x) & y & t(y)
  } else {
    adjacency<-distances<marker_diameter_mm
  }
  diag(adjacency)<-FALSE
  unseen<-seq_len(n);groups<-list()
  while(length(unseen)) {
    component<-unseen[1];frontier<-component
    while(length(frontier)) {
      more<-setdiff(which(apply(adjacency[frontier,,drop=FALSE],2,any)),component)
      component<-c(component,more);frontier<-more
    }
    unseen<-setdiff(unseen,component)
    if(length(component)>1)groups[[length(groups)+1L]]<-list(
      labels=sort(as.character(sites$label[component]),method='radix'),
      minimum_separation_mm=min(distances[component,component][distances[component,component]>0],Inf),
      coincident=any(distances[component,component][upper.tri(distances[component,component])]==0))
  }
  groups
}

# Resolve labels once on the final physical Cairo device, then retain the native
# vector scene for PNG/SVG/PDF. Otherwise ggrepel can re-solve on each device.
# grid.force/grid.grab use the public grid APIs documented at:
# https://stat.ethz.ch/R-manual/R-devel/library/grid/html/grid.force.html
# https://stat.ethz.ch/R-manual/R-devel/library/grid/html/grid.grab.html
# This is a size-bound export object; a new physical size requires re-solving.
ordination_freeze_layout_r <- function(plot,size_mm,font_family=NULL) {
  if(!is.numeric(size_mm) || length(size_mm)!=2L || any(!is.finite(size_mm)) || any(size_mm<=0))
    stop('Two finite positive final dimensions in millimetres are required')
  if(is.null(font_family))font_family<-if(exists('light_chart_family',mode='function'))
    light_chart_family('en') else 'sans'
  if(length(font_family)!=1L || !is.character(font_family) || is.na(font_family) || !nzchar(font_family))
    stop('A resolved native font family is required')
  if(!inherits(plot,'patchwork') && !inherits(plot,'ggplot') && !grid::is.grob(plot))
    stop('A native ggplot, patchwork or grid grob is required')
  temporary<-tempfile(fileext='.pdf')
  grDevices::cairo_pdf(temporary,width=size_mm[1]/25.4,height=size_mm[2]/25.4,family=font_family)
  on.exit({grDevices::dev.off();unlink(temporary)},add=TRUE)
  grob<-if(inherits(plot,'patchwork'))patchwork::patchworkGrob(plot) else
    if(inherits(plot,'ggplot'))ggplot2::ggplotGrob(plot) else plot
  if(exists('lc_native_text',mode='function'))grob<-lc_native_text(grob)
  grid::grid.newpage();grid::grid.draw(grob)
  geometry<-ordination_label_geometry_r() # Forces at-drawing-time text children.
  structure(list(grob=grid::grid.grab(wrap=TRUE),geometry=geometry,size_mm=as.numeric(size_mm),
    cairo_device_mm=grDevices::dev.size('in')*25.4),
    class='light_chart_frozen_ordination')
}

ordination_draw_frozen_r <- function(object) {
  if(!inherits(object,'light_chart_frozen_ordination'))stop('Resolve the native ordination layout before exporting')
  # Cairo rounds pages to whole PostScript points (1 pt = 0.3528 mm); raster
  # devices round to pixels. Accept that bounded rounding, not a resized figure.
  actual_size<-grDevices::dev.size('in')*25.4
  if(any(abs(actual_size-object$size_mm)>.36))
    stop(sprintf('Frozen native layout size %s mm differs from device %s mm; resolve at the new final size',
      paste(round(object$size_mm,3),collapse=' x '),paste(round(actual_size,3),collapse=' x ')))
  grid::grid.newpage();grid::grid.draw(object$grob)
  invisible(object)
}

# Deterministic category-internal packing. Only horizontal display positions
# change; category identity and measured y values are retained in the result.
ordinal_display_positions_r <- function(values, categories, ids,
                                         max_offset=.32, x_step=.16, y_separation=.07) {
  if (!is.numeric(values) || any(!is.finite(values)) || !is.factor(categories) ||
      length(values)!=length(categories) || length(values)!=length(ids) ||
      anyNA(categories) || anyNA(ids) || anyDuplicated(ids) ||
      !is.finite(max_offset) || !is.finite(x_step) || !is.finite(y_separation) ||
      max_offset<=0 || max_offset>=.5 || x_step<=0 || x_step>max_offset || y_separation<=0)
    stop('Finite values, explicit category levels, unique IDs and valid display packing bounds required')
  offsets<-rep(0,length(values))
  choices<-c(0,as.vector(rbind(seq(x_step,max_offset,by=x_step),
                              -seq(x_step,max_offset,by=x_step))))
  for (g in levels(categories)) {
    selected<-which(categories==g)
    selected<-selected[order(values[selected],as.character(ids[selected]))]
    placed<-integer()
    for(i in selected) {
      near<-placed[abs(values[placed]-values[i])<y_separation]
      allowed<-choices[vapply(choices,function(z)all(abs(z-offsets[near])>=x_step-1e-10),logical(1))]
      if(!length(allowed))stop('Insufficient category-internal display width; enlarge layout or explicitly revise packing parameters')
      offsets[i]<-allowed[1];placed<-c(placed,i)
    }
  }
  data.frame(id=as.character(ids),category=as.character(categories),
    category_center=as.integer(categories),display_offset=offsets,
    display_x=as.integer(categories)+offsets,measured_y=values,stringsAsFactors=FALSE)
}

# Opt-in enlargement of one physically unresolved native PCA marker cluster.
# Input geometry must come from the intended final-size plot. It fails rather
# than inventing offsets for exact coincidence or guessing multiple zooms.
ordination_overlap_enlargement_r <- function(pa,fit,id,group,palette,shapes,geometry) {
  d<-fit$scores
  if(!inherits(pa,'ggplot') || !is.data.frame(d) || !all(c(id,group,'PC1','PC2')%in%names(d)))
    stop('A native PCA score plot and its unchanged identity-mapped result are required')
  built<-ggplot2::ggplot_build(pa);b<-built$layout$panel_params[[1]]
  s<-geometry$sites;w<-geometry$width_mm;h<-geometry$height_mm
  if(!is.data.frame(s) || !setequal(as.character(d[[id]]),as.character(s$label)) ||
     length(w)!=1 || length(h)!=1 || !is.finite(w) || !is.finite(h) || min(w,h)<=0)
    stop('Measure this complete plot at its intended final physical size before requesting a zoom')
  aligned<-d[match(as.character(s$label),as.character(d[[id]])),,drop=FALSE]
  expected<-cbind((aligned$PC1-b$x.range[1])/diff(b$x.range)*w,
                 (aligned$PC2-b$y.range[1])/diff(b$y.range)*h)
  if(any(!is.finite(expected)) || max(abs(expected-as.matrix(s[c('point_x_mm','point_y_mm')])))>.2)
    stop('Measured geometry does not match this PCA plot; remeasure after any coordinate or scale change')
  point_layer<-which(vapply(pa$layers,function(layer)inherits(layer$geom,'GeomPoint'),logical(1)))
  if(length(point_layer)!=1L)stop('Measure one unchanged native marker layer before requesting an enlargement')
  current_markers<-pa$layers[[point_layer]]$geom$draw_panel(
    built$data[[point_layer]],b,built$layout$coord)
  # The geometry must describe these same shapes and native size/stroke gpar,
  # not merely unchanged centres with stale marker footprints.
  if(!all(c('marker_shape','marker_fontsize_pt','marker_lwd','marker_radius_mm')%in%names(s)) ||
     any(!is.finite(s$marker_radius_mm)) || any(s$marker_radius_mm<=0) ||
     !identical(as.numeric(s$marker_shape),as.numeric(rep_len(current_markers$pch,nrow(s)))) ||
     !isTRUE(all.equal(s$marker_fontsize_pt,as.numeric(rep_len(current_markers$gp$fontsize,nrow(s))))) ||
     !isTRUE(all.equal(s$marker_lwd,as.numeric(rep_len(current_markers$gp$lwd,nrow(s))))))
    stop('Marker shape or native pointsize/stroke changed; remeasure the current plot')
  clusters<-ordination_overlap_clusters_r(geometry,marker_diameter_mm=NULL)
  if(!length(clusters))return(list(plot=pa,decision=list(clusters=list(),inset=FALSE)))
  if(length(clusters)>1)stop('Multiple unresolved marker clusters: enlarge the layout or design explicit multiple enlargements')
  if(clusters[[1]]$coincident)stop('Exactly coincident points require an explicit multiplicity encoding; a zoom cannot separate them')
  selected<-clusters[[1]]$labels
  target<-d[as.character(d[[id]])%in%selected,,drop=FALSE]
  # Square source region in the same scientific coordinate units.
  half<-max(diff(range(target$PC1)),diff(range(target$PC2)))/2+
    .02*max(diff(b$x.range),diff(b$y.range))
  cx<-mean(range(target$PC1));cy<-mean(range(target$PC2))
  roi<-c(xmin=cx-half,xmax=cx+half,ymin=cy-half,ymax=cy+half)
  inside<-d$PC1>=roi['xmin'] & d$PC1<=roi['xmax'] & d$PC2>=roi['ymin'] & d$PC2<=roi['ymax']
  zoomfit<-fit;zoomfit$scores<-d[inside,,drop=FALSE]
  # Find an empty rectangle in physical panel coordinates. Protect both original
  # marker centers and actual text boxes, including the original overlapping pair.
  iw<-min(21,w*.39);ih<-min(21,h*.39)
  if(w-iw<=4 || h-ih<=4)stop('Insufficient final physical panel area for a truthful enlargement')
  candidates<-expand.grid(x=seq(2,w-iw-2,by=1),y=seq(2,h-ih-2,by=1))
  scored<-lapply(seq_len(nrow(candidates)),function(i) {
    x<-candidates$x[i];y<-candidates$y[i]
    point_clear<-sqrt(pmax(x-s$point_x_mm,0,s$point_x_mm-(x+iw))^2+
                      pmax(y-s$point_y_mm,0,s$point_y_mm-(y+ih))^2)
    label_clear<-sqrt(pmax(x-s$right_mm,0,s$left_mm-(x+iw))^2+
                      pmax(y-s$top_mm,0,s$bottom_mm-(y+ih))^2)
    # Preserve the existing1.5-mm visual clearance; enlarge it when an actual
    # native marker footprint requires more room. The radius bounds the native
    # outline, not a guessed interpretation of geom_point's size argument.
    clearance<-min(c(point_clear-pmax(1.5,s$marker_radius_mm),label_clear-.8))
    c(x=x,y=y,clearance=clearance)
  })
  scored<-do.call(rbind,scored);best<-scored[which.max(scored[,'clearance']),]
  if(best['clearance']<0)stop('No free physical area for a truthful local enlargement; enlarge/recompose figure')
  insetbox<-c(xmin=b$x.range[1]+best['x']/w*diff(b$x.range),
    xmax=b$x.range[1]+(best['x']+iw)/w*diff(b$x.range),
    ymin=b$y.range[1]+best['y']/h*diff(b$y.range),
    ymax=b$y.range[1]+(best['y']+ih)/h*diff(b$y.range))
  names(insetbox)<-c('xmin','xmax','ymin','ymax')
  family<-pa$theme$text$family
  if(is.null(family) || !nzchar(family))stop('Resolve the main plot font before requesting a matching enlargement')
  # Clone the actual mapped native plot, replacing only its identity-aligned
  # data subset. This retains the full overview's continuous color limits and
  # palette as well as category shapes, font and label controls. Refitting a
  # fresh wrapper here would silently recolor or rescale a continuous inset.
  zoomdata<-pa$data[as.character(pa$data[[id]])%in%as.character(zoomfit$scores[[id]]),,drop=FALSE]
  if(!all(c(id,'PC1','PC2')%in%names(zoomdata)) ||
     !setequal(as.character(zoomdata[[id]]),as.character(zoomfit$scores[[id]])))
    stop('The overview must retain its complete identity-mapped plot data')
  zoom<-pa+zoomdata+
    ggplot2::coord_equal(xlim=roi[c('xmin','xmax')],ylim=roi[c('ymin','ymax')],expand=FALSE,clip='off')+
    ggplot2::labs(x=NULL,y=NULL)+ggplot2::theme_void(base_family=family,base_size=7.5)+
    ggplot2::theme(legend.position='none',plot.margin=ggplot2::margin(3,3,3,3),
      panel.background=ggplot2::element_rect(fill='white',color='#8D959B',linewidth=.25))
  # Keep the scientific ROI unchanged. Cut short gaps in its outline and the
  # straight connector wherever actually measured text or marker envelopes lie.
  # This clips five fixed segments; it does not route a new arbitrary path,
  # cover marks with white patches, move a label, or expand the selected region.
  label_fields<-c('left_mm','right_mm','bottom_mm','top_mm')
  if(!all(label_fields%in%names(s)) || any(!is.finite(as.matrix(s[label_fields]))) ||
     any(s$left_mm>=s$right_mm) || any(s$bottom_mm>=s$top_mm) ||
     !'font_size_pt'%in%names(s) || any(!is.finite(s$font_size_pt)) || any(s$font_size_pt<=0))
    stop('Measure actual label bounds before placing an enlargement outline')
  label_pad_x<-.35;marker_pad<-.2
  # Native string ink bounds can be shorter than a final PDF text run's full
  # ascent/descent box. Reserve an additional fifth of an em vertically so a
  # source-frame dash cannot sit against that device-level text boundary.
  label_pad_y<-.35+.2*s$font_size_pt*25.4/72
  label_boxes<-data.frame(xmin=s$left_mm-label_pad_x,xmax=s$right_mm+label_pad_x,
    ymin=s$bottom_mm-label_pad_y,ymax=s$top_mm+label_pad_y)
  marker_boxes<-data.frame(xmin=s$marker_left_mm-marker_pad,xmax=s$marker_right_mm+marker_pad,
    ymin=s$marker_bottom_mm-marker_pad,ymax=s$marker_top_mm+marker_pad)
  boxes<-rbind(label_boxes,marker_boxes)
  clip_segment<-function(start,end,name) {
    delta<-end-start;length_mm<-sqrt(sum(delta^2))
    if(length_mm<=0)stop('A source outline or connector has no physical length')
    blocked<-list()
    for(i in seq_len(nrow(boxes))) {
      interval<-c(0,1)
      for(j in 1:2) {
        bounds<-as.numeric(boxes[i,if(j==1)c('xmin','xmax') else c('ymin','ymax')])
        if(abs(delta[j])<1e-12) {
          if(start[j]<bounds[1] || start[j]>bounds[2]){interval<-c(1,0);break}
        } else {
          crossing<-sort((bounds-start[j])/delta[j])
          interval<-c(max(interval[1],crossing[1]),min(interval[2],crossing[2]))
          if(interval[1]>interval[2])break
        }
      }
      if(interval[1]<=interval[2])blocked[[length(blocked)+1L]]<-interval
    }
    visible<-list();cursor<-0
    if(length(blocked)) {
      blocked<-do.call(rbind,blocked);blocked<-blocked[order(blocked[,1]),,drop=FALSE]
      for(i in seq_len(nrow(blocked))) {
        if(blocked[i,1]>cursor)visible[[length(visible)+1L]]<-c(cursor,blocked[i,1])
        cursor<-max(cursor,blocked[i,2])
      }
    }
    if(cursor<1)visible[[length(visible)+1L]]<-c(cursor,1)
    rows<-lapply(visible,function(v) {
      if(diff(v)*length_mm<.15)return(NULL)
      a<-start+v[1]*delta;z<-start+v[2]*delta
      data.frame(part=name,x=a[1],y=a[2],xend=z[1],yend=z[2],
        length_mm=diff(v)*length_mm,stringsAsFactors=FALSE)
    })
    rows<-Filter(Negate(is.null),rows)
    if(!length(rows)) {
      if(name=='connector')stop('No readable connector remains after protecting labels and marks; enlarge/recompose figure')
      return(data.frame(part=character(),x=numeric(),y=numeric(),xend=numeric(),yend=numeric(),length_mm=numeric()))
    }
    drawn<-do.call(rbind,rows)
    if(name=='connector' && sum(drawn$length_mm)<min(.75,length_mm*.25))
      stop('Connector is too obscured by labels and marks; enlarge/recompose figure')
    drawn
  }
  mm<-function(x,y)c((x-b$x.range[1])/diff(b$x.range)*w,
                      (y-b$y.range[1])/diff(b$y.range)*h)
  ll<-mm(roi['xmin'],roi['ymin']);lr<-mm(roi['xmax'],roi['ymin'])
  ul<-mm(roi['xmin'],roi['ymax']);ur<-mm(roi['xmax'],roi['ymax'])
  segments_mm<-rbind(clip_segment(ll,lr,'bottom'),clip_segment(lr,ur,'right'),
    clip_segment(ur,ul,'top'),clip_segment(ul,ll,'left'),
    clip_segment(ur,mm(insetbox['xmin'],insetbox['ymax']),'connector'))
  frame_perimeter<-2*(sqrt(sum((lr-ll)^2))+sqrt(sum((ul-ll)^2)))
  visible_fraction<-sum(segments_mm$length_mm[segments_mm$part!='connector'])/frame_perimeter
  if(visible_fraction<.5 || length(unique(segments_mm$part[segments_mm$part!='connector']))<3L)
    stop('Source outline is too obscured by labels and marks; enlarge/recompose figure')
  segments<-segments_mm
  for(field in c('x','xend'))segments[[field]]<-b$x.range[1]+segments_mm[[field]]/w*diff(b$x.range)
  for(field in c('y','yend'))segments[[field]]<-b$y.range[1]+segments_mm[[field]]/h*diff(b$y.range)
  frame<-segments[segments$part!='connector',,drop=FALSE]
  link<-segments[segments$part=='connector',,drop=FALSE]
  # Lock the measured overview ranges. Annotation coordinates must not retrain
  # its axes and thereby move the labels away from the bounds used above.
  main<-pa+ggplot2::coord_equal(xlim=b$x.range,ylim=b$y.range,expand=FALSE,clip='off')+
    ggplot2::annotate('segment',x=frame$x,y=frame$y,xend=frame$xend,yend=frame$yend,
      color='#8D959B',linewidth=.25,linetype='dotted')+
    ggplot2::annotate('segment',x=link$x,y=link$y,xend=link$xend,yend=link$yend,
      color='#A4A9AD',linewidth=.2,linetype='dotted')+
    ggplot2::annotation_custom(ggplot2::ggplotGrob(zoom),
      xmin=insetbox['xmin'],xmax=insetbox['xmax'],ymin=insetbox['ymin'],ymax=insetbox['ymax'])
  list(plot=main,detail_plot=zoom,decision=list(inset=TRUE,clusters=clusters,source_region=as.list(roi),
    inset_region=as.list(insetbox),source_sites=as.character(zoomfit$scores[[id]]),
    source_coordinates=zoomfit$scores[c(id,'PC1','PC2')],
    placement='Maximum physical clearance over 1-mm candidate grid, protecting actual text bounds and markers',
    minimum_clearance_mm=unname(best['clearance']),intended_size_mm=c(iw,ih),
    annotation_geometry=list(segments_mm=segments_mm,segments_scores=segments,
      label_horizontal_clearance_mm=label_pad_x,
      label_vertical_clearance_mm=stats::setNames(label_pad_y,s$label),
      marker_clearance_mm=marker_pad,
      visible_source_outline_fraction=visible_fraction,
      method='Unchanged ROI and straight connector; fixed segments clipped at measured native label and marker bounds'),
    scientific_boundary='Enlargement only; no recomputation, jitter, exclusions or changed coordinates'))
}

