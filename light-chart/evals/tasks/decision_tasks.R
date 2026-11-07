# Export untouched built-in observations, then draw a selected native-R task.
args <- commandArgs(trailingOnly=TRUE)
mode <- args[[1]]; pkg <- normalizePath(args[[2]],mustWork=TRUE); out <- args[[3]]
dir.create(out,recursive=TRUE,showWarnings=FALSE)
if(mode=="data") {
  write.csv(datasets::sleep,file.path(out,"sleep.csv"),row.names=FALSE)
  write.csv(datasets::Orange,file.path(out,"Orange.csv"),row.names=FALSE)
  write.csv(datasets::faithful,file.path(out,"faithful.csv"),row.names=FALSE)
  d <- survival::veteran
  d$id <- seq_len(nrow(d));d$group <- ifelse(d$trt==1,"Standard","Test")
  write.csv(d[,c("id","time","status","group")],file.path(out,"veteran.csv"),row.names=FALSE)
  cat("RAW_OBSERVATIONS_EXPORTED\n")
} else {
  source(file.path(pkg,"scripts/publication.R"),encoding="UTF-8")
  source(file.path(pkg,"scripts/domain_plots.R"),encoding="UTF-8")
  use_project_style(file.path(out,"project-style.json"))
  selection <- jsonlite::read_json(file.path(out,"T04_survival.plan.json"))
  stopifnot(selection$status=="ready",selection$recommended$construction=="kaplan-meier-risk")
  d <- read.csv(file.path(out,"veteran.csv"))
  result <- survival_panel_r(d,"time","status","group","id",c(0,250,500,750,1000),
    palette=lc_colors(c("Standard","Test")),time_label="Follow-up (days)",group_order=c("Standard","Test"))
  result$plot <- result$plot+patchwork::plot_annotation(theme=ggplot2::theme(
    plot.margin=ggplot2::margin(7,10,7,10)))
  save_figure_r(result$plot,file.path(out,"T04_survival"),width_mm=132,height_mm=104)
  write.csv(result$curve,file.path(out,"T04_curve.csv"),row.names=FALSE)
  write.csv(result$risk,file.path(out,"T04_risk.csv"),row.names=FALSE)
  for(i in seq_len(nrow(result$risk))) stopifnot(result$risk$n[i]==sum(
    d$group==result$risk$group[i]&d$time>=result$risk$time[i]))
  jsonlite::write_json(list(subjects=nrow(d),events=sum(d$status),risk_counts_verified=TRUE,
    definitions=result$definitions,backend="native R"),file.path(out,"T04_checks.json"),pretty=TRUE,auto_unbox=TRUE)
  cat("NATIVE_R_TASK_COMPLETE\n")
}
