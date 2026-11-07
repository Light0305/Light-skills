# Regression for a real final-size source-frame/label collision, checked in R
# geometry and the actual exported PDF rather than by matching implementation.
script<-sub('^--file=','',grep('^--file=',commandArgs(),value=TRUE)[1])
root<-normalizePath(file.path(dirname(script),'..'),mustWork=TRUE)
source(file.path(root,'skills/light-chart/scripts/publication.R'))
source(file.path(root,'skills/light-chart/scripts/ordination.R'))
library(ggplot2)
raw<-read.csv(file.path(root,'artifacts/nature-backbone-rebuild/tasks/dune/data/dune.csv'),
  check.names=FALSE,colClasses=c(site_id='character'))
meta<-read.csv(file.path(root,'artifacts/nature-backbone-rebuild/tasks/dune/data/dune_environment.csv'),
  colClasses=c(site_id='character'))
fit<-hellinger_pca_r(raw,meta,'site_id',setdiff(names(raw),'site_id'),
  'vegetation cover class',c('Management','A1'))
shapes<-c(BF=16,HF=17,NM=15,SF=18)
p<-ordination_plot_r(fit,'site_id','Management',shapes=shapes,color_by='A1',
  color_limits=range(meta$A1),color_colors=c('#94BBA5','#176541'),
  color_label='A1 soil horizon',font_size=7.5,font_family='Arial')
size<-c(110,105);frozen<-ordination_freeze_layout_r(p,size,'Arial')
geometry<-frozen$geometry[[1]];sites<-geometry$sites
zoom<-ordination_overlap_enlargement_r(p,fit,'site_id','Management',NULL,shapes,geometry)
stopifnot(isTRUE(zoom$decision$inset))
segments<-zoom$decision$annotation_geometry$segments_mm
stopifnot(all(is.finite(as.matrix(segments[c('x','y','xend','yend')]))),
  zoom$decision$annotation_geometry$visible_source_outline_fraction>=.5)

# Independent segment-intersection test using orientation/corner geometry. The
# implementation uses parameter intervals; this test does not call that logic.
cross<-function(a,b,c)(b[1]-a[1])*(c[2]-a[2])-(b[2]-a[2])*(c[1]-a[1])
on_line<-function(a,b,c)all(c>=pmin(a,b)-1e-9 & c<=pmax(a,b)+1e-9)
intersects<-function(a,b,c,d) {
  values<-c(cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b))
  if(values[1]*values[2]<0 && values[3]*values[4]<0)return(TRUE)
  (abs(values[1])<1e-9 && on_line(a,b,c)) || (abs(values[2])<1e-9 && on_line(a,b,d)) ||
    (abs(values[3])<1e-9 && on_line(c,d,a)) || (abs(values[4])<1e-9 && on_line(c,d,b))
}
hits_box<-function(row,box) {
  a<-unname(as.numeric(row[c('x','y')]));b<-unname(as.numeric(row[c('xend','yend')]))
  inside<-function(z)z[1]>=box[1] && z[1]<=box[2] && z[2]>=box[3] && z[2]<=box[4]
  if(inside(a) || inside(b))return(TRUE)
  corners<-rbind(c(box[1],box[3]),c(box[2],box[3]),c(box[2],box[4]),c(box[1],box[4]))
  any(vapply(1:4,function(i)intersects(a,b,corners[i,],corners[if(i==4)1 else i+1,]),logical(1)))
}
# The uncut v1 rectangle truly intersects measured labels on this development
# input. Keeping this assertion proves the case still exercises the defect.
b<-ggplot_build(p)$layout$panel_params[[1]];roi<-unlist(zoom$decision$source_region)
mm<-function(x,y)c((x-b$x.range[1])/diff(b$x.range)*geometry$width_mm,
  (y-b$y.range[1])/diff(b$y.range)*geometry$height_mm)
ll<-mm(roi['xmin'],roi['ymin']);lr<-mm(roi['xmax'],roi['ymin'])
ul<-mm(roi['xmin'],roi['ymax']);ur<-mm(roi['xmax'],roi['ymax'])
raw_edges<-data.frame(x=c(ll[1],lr[1],ur[1],ul[1]),y=c(ll[2],lr[2],ur[2],ul[2]),
  xend=c(lr[1],ur[1],ul[1],ll[1]),yend=c(lr[2],ur[2],ul[2],ll[2]))
original_hits<-0L
for(i in seq_len(nrow(sites))) {
  box<-unname(as.numeric(sites[i,c('left_mm','right_mm','bottom_mm','top_mm')]))
  original_hits<-original_hits+sum(vapply(seq_len(nrow(raw_edges)),
    function(j)hits_box(raw_edges[j,],box),logical(1)))
  # Less than the helper's clearance, leaving numerical boundary tolerance.
  protected<-box+c(-.3,.3,-.75,.75)
  stopifnot(!any(vapply(seq_len(nrow(segments)),function(j)hits_box(segments[j,],protected),logical(1))))
  marker<-unname(as.numeric(sites[i,c('marker_left_mm','marker_right_mm','marker_bottom_mm','marker_top_mm')]))+
    c(-.1,.1,-.1,.1)
  stopifnot(!any(vapply(seq_len(nrow(segments)),function(j)hits_box(segments[j,],marker),logical(1))))
}
stopifnot(original_hits>0)
final<-ordination_freeze_layout_r(zoom$plot,size,'Arial')
after<-final$geometry[[1]]$sites;after<-after[match(sites$label,after$label),]
fields<-c('point_x_mm','point_y_mm','text_x_mm','text_y_mm','left_mm','right_mm','bottom_mm','top_mm')
movement<-max(abs(as.matrix(sites[fields])-as.matrix(after[fields])))
stopifnot(identical(sites$label,after$label),movement<1e-7)
before_built<-ggplot_build(p);after_built<-ggplot_build(zoom$plot)
point<-which(vapply(p$layers,function(z)inherits(z$geom,'GeomPoint'),logical(1)))
for(field in c('x','y','shape','colour'))
  stopifnot(identical(before_built$data[[point]][[field]],after_built$data[[point]][[field]]))
stopifnot(identical(before_built$layout$panel_params[[1]]$x.range,after_built$layout$panel_params[[1]]$x.range),
  identical(before_built$layout$panel_params[[1]]$y.range,after_built$layout$panel_params[[1]]$y.range))
args<-commandArgs(trailingOnly=TRUE)
out<-if(length(args))args[1] else tempfile('ordination-annotation-')
dir.create(out,recursive=TRUE,showWarnings=FALSE)
qa<-save_figure_r(final,file.path(out,'annotation-regression'),width_mm=size[1],height_mm=size[2],
  draw=ordination_draw_frozen_r,review_plots=list(overview=p,detail=zoom$detail_plot))
stopifnot(qa$automated_status!='FAIL',length(qa$failures)==0)
jsonlite::write_json(list(original_uncut_text_intersections=original_hits,
  final_overview_point_and_label_movement_mm=movement,drawn_segments_mm=segments,
  source_region=zoom$decision$source_region,source_ids=zoom$decision$source_sites,
  pdf_status=qa$automated_status),file.path(out,'regression-checks.json'),
  auto_unbox=TRUE,pretty=TRUE,digits=NA)
cat('ORDINATION_ANNOTATION_NATIVE_PDF_PASS\n')
