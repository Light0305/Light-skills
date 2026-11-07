# Real native-device checks, not a snapshot of implementation text.
script<-sub('^--file=','',grep('^--file=',commandArgs(),value=TRUE)[1])
root<-normalizePath(file.path(dirname(script),'..'),mustWork=TRUE)
source(file.path(root,'skills/light-chart/scripts/ordination.R'))
library(ggplot2)
raw<-read.csv(file.path(root,'artifacts/nature-backbone-rebuild/tasks/dune/data/dune.csv'),check.names=FALSE,colClasses=c(site_id='character'))
meta<-read.csv(file.path(root,'artifacts/nature-backbone-rebuild/tasks/dune/data/dune_environment.csv'),colClasses=c(site_id='character'))
fit<-hellinger_pca_r(raw,meta,'site_id',setdiff(names(raw),'site_id'),'vegetation cover class','Management')
palette<-c(BF='#4477AA',HF='#EE6677',NM='#228833',SF='#AA3377')
shapes<-c(BF=16,HF=17,NM=15,SF=18)
make<-function(object)ordination_plot_r(object,'site_id','Management',palette,shapes,font_size=8,font_family='Arial')
size<-c(95,90)
first<-ordination_freeze_layout_r(make(fit),size,font_family='Arial')
set.seed(61);shuffled<-fit;shuffled$scores<-fit$scores[sample(nrow(fit$scores)),]
second<-ordination_freeze_layout_r(make(shuffled),size,font_family='Arial')
a<-first$geometry[[1]]$sites;b<-second$geometry[[1]]$sites
stopifnot(identical(a$label,b$label),setequal(a$label,raw$site_id),nrow(a)==20)
stopifnot(max(abs(as.matrix(a[c('point_x_mm','point_y_mm','text_x_mm','text_y_mm')])-as.matrix(b[c('point_x_mm','point_y_mm','text_x_mm','text_y_mm')])) )<1e-9)
expect_error<-function(expr){ok<-tryCatch({force(expr);FALSE},error=function(e)TRUE);stopifnot(ok)}
temporary<-tempfile();dir.create(temporary)
grDevices::cairo_pdf(file.path(temporary,'frozen.pdf'),width=size[1]/25.4,height=size[2]/25.4,family='Arial')
ordination_draw_frozen_r(first);pdfgeom<-ordination_label_geometry_r();grDevices::dev.off()
ragg::agg_png(file.path(temporary,'frozen.png'),width=size[1],height=size[2],units='mm',res=300)
ordination_draw_frozen_r(first);pnggeom<-ordination_label_geometry_r();grDevices::dev.off()
stopifnot(length(pdfgeom)==1,length(pnggeom)==1)
# Raster pixel rounding may change the physical page by a fraction of a pixel;
# the resolved label tree must not solve again or lose any site.
ga<-pdfgeom[[1]]$sites;gb<-pnggeom[[1]]$sites
stopifnot(identical(ga$label,gb$label))
fields<-c('point_x_mm','point_y_mm','text_x_mm','text_y_mm')
stopifnot(max(abs(as.matrix(ga[fields])-as.matrix(gb[fields])))<.2)
grDevices::pdf(file.path(temporary,'wrong-size.pdf'),width=5,height=5)
expect_error(ordination_draw_frozen_r(first));grDevices::dev.off()
# Long identities survive; this measures their real boxes, without pretending
# that a crowded physical canvas can always provide collision-free labels.
long<-fit;long$scores$site_id<-paste0('Station-',sprintf('%03d',as.integer(long$scores$site_id)))
longdraw<-ordination_freeze_layout_r(make(long),c(120,110),'Arial')
stopifnot(setequal(longdraw$geometry[[1]]$sites$label,long$scores$site_id),
  all(is.finite(longdraw$geometry[[1]]$sites$left_mm)))
# The same overlap detector and placement work with alternate IDs and row order;
# the crop retains actual PCA coordinates rather than jittering close sites.
zoom<-ordination_overlap_enlargement_r(make(fit),fit,'site_id','Management',palette,shapes,first$geometry[[1]])
zoom2<-ordination_overlap_enlargement_r(make(shuffled),shuffled,'site_id','Management',palette,shapes,second$geometry[[1]])
stopifnot(isTRUE(zoom$decision$inset),identical(zoom$decision$source_region,zoom2$decision$source_region))
longzoom<-ordination_overlap_enlargement_r(make(long),long,'site_id','Management',palette,shapes,longdraw$geometry[[1]])
stopifnot(isTRUE(longzoom$decision$inset),all(grepl('^Station-',longzoom$decision$source_sites)))
actual<-zoom$decision$source_coordinates
original<-fit$scores[match(actual$site_id,fit$scores$site_id),c('site_id','PC1','PC2')]
stopifnot(identical(unname(as.matrix(actual[c('PC1','PC2')])),unname(as.matrix(original[c('PC1','PC2')]))))
wrong<-first$geometry[[1]];wrong$sites$point_x_mm[1]<-wrong$sites$point_x_mm[1]+1
expect_error(ordination_overlap_enlargement_r(make(fit),fit,'site_id','Management',palette,shapes,wrong))
# Coincidence needs multiplicity, not an invented offset or meaningless zoom.
g<-list(sites=data.frame(label=c('x','y','z'),point_x_mm=c(0,0,10),point_y_mm=c(0,0,10)))
clusters<-ordination_overlap_clusters_r(g)
stopifnot(length(clusters)==1,isTRUE(clusters[[1]]$coincident),identical(clusters[[1]]$labels,c('x','y')))
expect_error(ordinal_display_positions_r(rep(0,8),factor(rep('A',8)),letters[1:8]))
expect_error(ordination_freeze_layout_r(make(fit),c(NA,90),'Arial'))
# Real native footprint boundary: ggplot size2.1/stroke.45 is not a2.1-mm
# diameter for every shape. Same-row triangles2.2mm apart have overlapping
# native envelopes; at2.6mm they do not. Circles2.2mm apart also do not.
triangle_palette<-c(T='#000000');triangle_shapes<-c(T=17)
fixture<-list(scores=data.frame(site_id=c('north','south'),PC1=c(8,9),PC2=c(10,10),Management=c('T','T')),variance=c(.6,.3))
native_plot<-function(object,shape=17)ordination_plot_r(object,'site_id','Management',triangle_palette,c(T=shape),font_size=8,font_family='Arial')+
  ggplot2::coord_equal(xlim=c(0,20),ylim=c(0,20),expand=FALSE,clip='off')
initial<-ordination_freeze_layout_r(native_plot(fixture),c(90,90),'Arial')
footprint_cases<-list()
for(case in list(list(name='triangles2.2mm',gap=2.2,shape=17,overlap=TRUE),
                 list(name='triangles2.6mm',gap=2.6,shape=17,overlap=FALSE),
                 list(name='circles2.2mm',gap=2.2,shape=16,overlap=FALSE))) {
 f<-fixture;f$scores$PC1[2]<-f$scores$PC1[1]+case$gap/initial$geometry[[1]]$width_mm*20
 pp<-native_plot(f,case$shape);ff<-ordination_freeze_layout_r(pp,c(90,90),'Arial')
 gg<-ff$geometry[[1]];physical_gap<-abs(diff(gg$sites$point_x_mm))
 stopifnot(abs(physical_gap-case$gap)<1e-8)
 envelope<-ordination_overlap_clusters_r(gg,marker_diameter_mm=NULL)
 stopifnot(identical(length(envelope)>0,case$overlap))
 checked<-ordination_overlap_enlargement_r(pp,f,'site_id','Management',triangle_palette,c(T=case$shape),gg)
 stopifnot(identical(checked$decision$inset,case$overlap))
 if(case$shape==17)stopifnot(all(gg$sites$marker_right_mm-gg$sites$marker_left_mm>2.4),
   all(gg$sites$marker_right_mm-gg$sites$marker_left_mm<2.5))
 if(case$overlap) {
   stopifnot(length(ordination_overlap_clusters_r(gg,marker_diameter_mm=2.1))==0)
   stopifnot(setequal(checked$decision$source_sites,f$scores$site_id))
 }
 footprint_cases[[case$name]]<-list(physical_gap_mm=physical_gap,shape=case$shape,
   native_envelopes=gg$sites[c('label','marker_left_mm','marker_right_mm','marker_bottom_mm','marker_top_mm')],
   possible_overlap=length(envelope)>0,adapter_zoom=checked$decision$inset,
   definition=gg$marker_footprint_method)
}
coincident<-fixture;coincident$scores$PC1<-c(8,8)
cp<-native_plot(coincident);cf<-ordination_freeze_layout_r(cp,c(90,90),'Arial')
expect_error(ordination_overlap_enlargement_r(cp,coincident,'site_id','Management',triangle_palette,triangle_shapes,cf$geometry[[1]]))
args<-commandArgs(trailingOnly=TRUE)
if(length(args))jsonlite::write_json(footprint_cases,args[1],pretty=TRUE,auto_unbox=TRUE,digits=NA)
cat('ORDINATION_LAYOUT_NATIVE_PASS\n')
