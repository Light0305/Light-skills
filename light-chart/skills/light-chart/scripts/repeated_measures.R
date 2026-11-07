# Native R shared-scale repeated-unit small multiples. Sources: nature's
# r-workflow device/ggplot contract; SciPilot chart_selection >6 trajectories;
# figures4papers BrainTeaser complete case's fixed scales and legend corridor.
# Data remain raw: no automatic baseline, model, mean, CI or interpolation.
repeated_trajectory_r <- function(data, unit, x, y, unit_order, x_unit, y_unit,
                                  ncol = 4L, color = '#24648A',
                                  font_family = NULL, font_size = NULL,
                                  x_limits = NULL, y_limits = NULL) {
  if(!requireNamespace('ggplot2', quietly=TRUE)) stop('Missing R package: ggplot2',call.=FALSE)
  fields <- c(unit,x,y)
  if(!is.data.frame(data) || !nrow(data) || anyDuplicated(names(data)) ||
     length(unique(fields))!=3L || !all(fields %in% names(data)))
    stop('Nonempty repeated data need distinct existing unit/x/y fields',call.=FALSE)
  if(length(x_unit)!=1L || length(y_unit)!=1L || !is.character(x_unit) || !is.character(y_unit) ||
     is.na(x_unit) || is.na(y_unit) || !nzchar(trimws(x_unit)) || !nzchar(trimws(y_unit)))
    stop('Explicit x_unit and y_unit required',call.=FALSE)
  if(anyNA(data[[unit]]) || is.logical(data[[unit]])) stop('Nonmissing unit identities required',call.=FALSE)
  ids <- as.character(data[[unit]]); declared <- as.character(unit_order)
  if(!length(declared) || anyNA(declared) || anyDuplicated(declared) ||
     !setequal(ids,declared) || length(unique(data[[unit]]))!=length(unique(ids)))
    stop('Unit order must exactly match observed identities',call.=FALSE)
  for(k in c(x,y)) {
    if(!is.numeric(data[[k]]) || is.complex(data[[k]]) || any(!is.finite(data[[k]])))
      stop('Finite real numeric trajectory measurements required; no implicit row deletion',call.=FALSE)
  }
  if(length(ncol)!=1L || !is.numeric(ncol) || !is.finite(ncol) || ncol<1 || ncol!=floor(ncol))
    stop('Positive integer facet column count required',call.=FALSE)
  # Internal names are confined to the returned rendering table. The explicit
  # source columns and source row positions remain in manifest.
  d <- data.frame(.lc_unit=factor(ids,levels=declared), .lc_x=data[[x]],
                  .lc_y=data[[y]], .lc_source_position=seq_len(nrow(data))-1L)
  if(anyDuplicated(d[c('.lc_unit','.lc_x')])) stop('Duplicate unit/x rows need explicit repeat handling',call.=FALSE)
  if(any(table(d$.lc_unit)<2L)) stop('Every unit needs at least two observations',call.=FALSE)
  d <- d[order(d$.lc_unit,d$.lc_x),,drop=FALSE]; rownames(d)<-NULL
  bounded <- function(request, values, name) {
    if(is.null(request)) return(range(values))
    if(!is.numeric(request) || is.complex(request) || length(request)!=2L ||
       any(!is.finite(request)) || request[1]>=request[2] ||
       min(values)<request[1] || max(values)>request[2])
      stop(paste(name,'must preserve every observation'),call.=FALSE)
    request
  }
  xx <- bounded(x_limits,d$.lc_x,'x_limits'); yy <- bounded(y_limits,d$.lc_y,'y_limits')
  if(is.null(font_family)) font_family <- if(exists('lc_fonts')) lc_fonts()$latin else 'sans'
  if(is.null(font_size)) font_size <- if(exists('lc_project')) lc_project()$typography$base_pt else 7
  p <- ggplot2::ggplot(d,ggplot2::aes(x=.lc_x,y=.lc_y,group=.lc_unit))+
    ggplot2::geom_line(color=color,linewidth=.35)+
    ggplot2::geom_point(color=color,size=.8)+
    ggplot2::facet_wrap(ggplot2::vars(.lc_unit),ncol=as.integer(ncol),scales='fixed',drop=FALSE)+
    ggplot2::coord_cartesian(xlim=xx,ylim=yy)+
    ggplot2::labs(x=paste0(x,' (',x_unit,')'),y=paste0(y,' (',y_unit,')'))+
    ggplot2::theme_classic(base_size=font_size,base_family=font_family)+
    ggplot2::theme(strip.background=ggplot2::element_blank(),
      strip.text=ggplot2::element_text(size=font_size),
      axis.text=ggplot2::element_text(size=font_size,color='#30343A'),
      axis.ticks=ggplot2::element_line(linewidth=.25),
      axis.line=ggplot2::element_line(linewidth=.3),legend.position='none')
  traces <- lapply(declared,function(id) {
    part<-d[as.character(d$.lc_unit)==id,,drop=FALSE]
    list(unit_id=id,source_positions=part$.lc_source_position,x=part$.lc_x,y=part$.lc_y)
  })
  list(plot=p,data=d,manifest=list(unit_field=unit,x_field=x,y_field=y,
    unit_order=declared,unit_count=length(declared),rows=nrow(data),traces=traces,
    shared_x_limits=xx,shared_y_limits=yy,x_unit=x_unit,y_unit=y_unit,
    rows_are_independent_units=FALSE,baseline_inferred=FALSE,
    boundary='Raw repeated trajectories, fixed scales; no model, baseline adjustment, CI or inference.'))
}
