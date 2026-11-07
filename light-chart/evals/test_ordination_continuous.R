# Native continuous metadata mapping, identity, physical scale and zoom invariants.
script<-sub('^--file=','',grep('^--file=',commandArgs(),value=TRUE)[1])
root<-normalizePath(file.path(dirname(script),'..'),mustWork=TRUE)
source(file.path(root,'skills/light-chart/scripts/ordination.R'))
source(file.path(root,'skills/light-chart/scripts/review_tools.R'))
library(ggplot2)
expect_error<-function(expr){ok<-tryCatch({force(expr);FALSE},error=function(e)TRUE);stopifnot(ok)}
raw<-data.frame(site=c('north','south','west','east'),a=c(2,3,0,1),b=c(0,1,4,2),c=c(1,0,1,4))
meta<-data.frame(site=rev(raw$site),group=c('B','A','B','A'),soil_pH=c(6.7,5.3,7.1,4.8))
fit<-hellinger_pca_r(raw,meta,'site',c('a','b','c'),'measured development fixture',c('group','soil_pH'))
shapes<-c(A=16,B=17);ramp<-c('#94BBA5','#176541');limits<-c(4.5,7.5)
make<-function(object)ordination_plot_r(object,'site','group',shapes=shapes,
  color_by='soil_pH',color_limits=limits,color_colors=ramp,color_label='Soil pH',font_family='Arial')
p<-make(fit);built<-ggplot_build(p)
stopifnot(identical(p$data$site,sort(raw$site)),
  identical(p$data$.continuous_color,meta$soil_pH[match(p$data$site,meta$site)]))
color_scale<-built$plot$scales$get_scales('colour')
stopifnot(inherits(color_scale,'ScaleContinuous'),inherits(color_scale$guide,'GuideColourbar'),
  identical(color_scale$get_limits(),limits),identical(color_scale$name,'Soil pH'))
layer<-which(vapply(p$layers,function(z)inherits(z$geom,'GeomPoint'),logical(1)))
stopifnot(identical(unname(built$data[[layer]]$colour),unname(color_scale$map(p$data$soil_pH))),
  identical(as.numeric(built$data[[layer]]$shape),as.numeric(shapes[as.character(p$data$group)])))
frozen<-ordination_freeze_layout_r(p,c(110,100),'Arial')
geometry<-frozen$geometry[[1]]
ranges<-built$layout$panel_params[[1]]
stopifnot(abs(geometry$width_mm/diff(ranges$x.range)-geometry$height_mm/diff(ranges$y.range))<1e-8,
  setequal(geometry$sites$label,raw$site))
shuffled<-fit;shuffled$scores<-fit$scores[c(3,1,4,2),]
second<-ordination_freeze_layout_r(make(shuffled),c(110,100),'Arial')
stopifnot(identical(frozen$geometry[[1]]$sites,second$geometry[[1]]$sites),
  identical(figure_snapshot_r(list(scores=p)),figure_snapshot_r(list(scores=make(shuffled)))))
bad<-fit;bad$scores$soil_pH[1]<-Inf;expect_error(make(bad))
bad<-fit;bad$scores$soil_pH<-as.character(bad$scores$soil_pH);expect_error(make(bad))
expect_error(ordination_plot_r(fit,'site','group',shapes=shapes,color_by='soil_pH',color_limits=c(5,6)))
expect_error(ordination_plot_r(fit,'site','group',shapes=shapes,color_by='absent'))
# A known close triangle pair exercises the real envelope/zoom boundary; a
# third site outside the ROI proves that the inset cannot retrain color limits.
fixture<-list(scores=data.frame(site=c('a','b','c'),PC1=c(8,9,18),PC2=c(10,10,18),
  group=c('A','A','B'),soil_pH=c(5,5.4,7.5)),variance=c(.6,.3))
zoom_make<-function(object)ordination_plot_r(object,'site','group',shapes=c(A=17,B=16),
  color_by='soil_pH',color_limits=c(4.5,8),color_colors=ramp,font_family='Arial')+
  coord_equal(xlim=c(0,20),ylim=c(0,20),expand=FALSE,clip='off')
initial<-ordination_freeze_layout_r(zoom_make(fixture),c(100,100),'Arial')
fixture$scores$PC1[2]<-fixture$scores$PC1[1]+2.2/initial$geometry[[1]]$width_mm*20
main<-zoom_make(fixture);measured<-ordination_freeze_layout_r(main,c(100,100),'Arial')
zoom<-ordination_overlap_enlargement_r(main,fixture,'site','group',NULL,c(A=17,B=16),measured$geometry[[1]])
stopifnot(isTRUE(zoom$decision$inset),setequal(zoom$detail_plot$data$site,c('a','b')))
main_built<-ggplot_build(main);detail_built<-ggplot_build(zoom$detail_plot)
main_color<-main_built$plot$scales$get_scales('colour')
detail_color<-detail_built$plot$scales$get_scales('colour')
stopifnot(identical(main_color$get_limits(),detail_color$get_limits()),
  identical(main_color$map(fixture$scores$soil_pH),detail_color$map(fixture$scores$soil_pH)))
selected<-match(zoom$detail_plot$data$site,main$data$site)
stopifnot(identical(main_built$data[[layer]]$colour[selected],detail_built$data[[layer]]$colour),
  identical(main_built$data[[layer]]$shape[selected],detail_built$data[[layer]]$shape),
  identical(main_built$data[[layer]]$x[selected],detail_built$data[[layer]]$x),
  identical(main_built$data[[layer]]$y[selected],detail_built$data[[layer]]$y))
cat('ORDINATION_CONTINUOUS_NATIVE_PASS\n')
