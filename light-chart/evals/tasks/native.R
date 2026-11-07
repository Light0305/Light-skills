# End-to-end native R tasks and named raw inputs for the Python tasks.
args <- commandArgs(trailingOnly=TRUE)
options(warn=1)
pkg <- normalizePath(args[[1]],mustWork=TRUE)
out <- args[[2]]; dir.create(out,recursive=TRUE,showWarnings=FALSE)
source(file.path(pkg,"scripts/publication.R"),encoding="UTF-8")
source(file.path(pkg,"scripts/domain_plots.R"),encoding="UTF-8")
use_project_style(args[[3]])

write.csv(datasets::faithful,file.path(out,"faithful.csv"),row.names=FALSE)
anorexia <- MASS::anorexia; anorexia$subject <- sprintf("S%03d",seq_len(nrow(anorexia)))
write.csv(anorexia,file.path(out,"anorexia.csv"),row.names=FALSE)
write.csv(datasets::state.x77,file.path(out,"state_x77.csv"),row.names=TRUE)

raw <- datasets::mtcars
features <- c("mpg","disp","hp","drat","wt","qsec","carb")
mat <- t(scale(as.matrix(raw[,features])))
metadata <- data.frame(sample=rownames(raw),Transmission=ifelse(raw$am==0,"Automatic","Manual"))
metadata <- metadata[rev(seq_len(nrow(metadata))),]
bound <- ceiling(max(abs(mat))*2)/2
ht <- annotated_heatmap_r(mat,metadata,"sample","Transmission",
  list(Transmission=lc_colors(c("Automatic","Manual"))),limits=c(-bound,bound),center=0,
  cluster_rows=TRUE,cluster_columns=TRUE,
  column_split=factor(paste0(raw$cyl," cylinders"),levels=c("4 cylinders","6 cylinders","8 cylinders")),
  name="Row z score",show_column_names=TRUE)
draw <- function(x) {grid::grid.newpage();ComplexHeatmap::draw(x,newpage=FALSE,
  padding=grid::unit(rep(5,4),"mm"),heatmap_legend_side="right",annotation_legend_side="right")}
save_figure_r(ht,file.path(out,"T03_annotated_heatmap"),width_mm=180,height_mm=124,draw=draw)
write.csv(raw,file.path(out,"mtcars.csv"),row.names=TRUE)
write.csv(mat,file.path(out,"mtcars_z.csv"),row.names=TRUE)
write.csv(metadata,file.path(out,"mtcars_metadata.csv"),row.names=FALSE)

d <- survival::lung;d$id <- seq_len(nrow(d));d$event <- d$status-1L
d$group <- ifelse(d$sex==1,"Male","Female")
km <- survival_panel_r(d,"time","event","group","id",c(0,250,500,750,1000),
  palette=lc_colors(c("Male","Female")),time_label="Follow-up (days)",group_order=c("Male","Female"))
km$plot <- km$plot+patchwork::plot_annotation(theme=ggplot2::theme(plot.margin=ggplot2::margin(7,10,7,10)))
save_figure_r(km$plot,file.path(out,"T04_survival"),width_mm=132,height_mm=102)
write.csv(d[,c("id","time","event","group")],file.path(out,"lung.csv"),row.names=FALSE)
write.csv(km$curve,file.path(out,"lung_curve.csv"),row.names=FALSE)
write.csv(km$risk,file.path(out,"lung_risk.csv"),row.names=FALSE)
for(i in seq_len(nrow(km$risk)))stopifnot(km$risk$n[i]==sum(d$group==km$risk$group[i]&d$time>=km$risk$time[i]))

# Export shared mappings for numeric cross-language verification.
jsonlite::write_json(list(groups=lc_colors(c("Control","CBT","FT","Male","Female")),
  palettes=lc_project()$palettes,fonts=lc_fonts(),minimum_pt=lc_project()$typography$minimum_pt,
  actual_diverging_colors=ht@matrix_color_mapping@col_fun(seq(-bound,bound,length.out=9)),
  survival=list(n=km$n,events=km$events,definitions=km$definitions),
  sources=list(paired="MASS::anorexia; young female anorexia patients; weights in pounds; descriptive",
    joint="datasets::faithful; Old Faithful eruptions and waiting times in minutes",
    network="datasets::state.x77; 50 US states, eight historical variables; Pearson correlations, descriptive")),
  file.path(out,"R_contract_and_sources.json"),pretty=TRUE,auto_unbox=TRUE)

# Explicit Latin/CJK runs on a native R PDF.
p <- lc_project();p$fonts <- list(latin="Times New Roman",cjk="SimSun",serif=TRUE)
jsonlite::write_json(p,file.path(out,"serif-project.json"),pretty=TRUE,auto_unbox=TRUE)
use_project_style(file.path(out,"serif-project.json"))
g <- mixed_text_grob("生存率 Survival 12.5%",x=grid::unit(.06,"npc"),fontsize=9)
draw_grob <- function(x){grid::grid.newpage();grid::grid.draw(x)}
save_figure_r(g,file.path(out,"font_mixed_R"),width_mm=90,height_mm=22,draw=draw_grob)
use_project_style(args[[3]])
mixed <- ggplot2::ggplot(data.frame(x=1:3,y=1:3),ggplot2::aes(x,y))+
  ggplot2::geom_point(colour=lc_color('primary'))+
  ggplot2::labs(x='时间 Time 12.5',y='响应 Response')+theme_light_chart(lang='zh')
save_figure_r(mixed,file.path(out,'font_ggplot_R'),width_mm=100,height_mm=70,lang='zh')
cat("NATIVE_TASKS_COMPLETE\n")
