args <- commandArgs(trailingOnly = TRUE)
source(args[[1]])
out <- args[[2]]
library(ggplot2)
library(patchwork)
dir.create(out, recursive = TRUE, showWarnings = FALSE)

groups <- data.frame(
  group = rep(c("Control", "Treatment"), each = 5),
  value = c(1.2, 1.5, 1.3, 1.7, 1.4, 2.1, 2.4, 2.0, 2.6, 2.3)
)
p1 <- ggplot(groups, aes(group, value, colour = group)) +
  geom_point(position = position_jitter(width = 0.06, seed = 71), size = 2) +
  scale_colour_manual(values = c("#0072B2", "#D55E00")) +
  labs(x = NULL, y = "Response (a.u.)") + theme_light_chart() + theme(legend.position = "none")
save_figure_r(p1, file.path(out, "A01_groups"), width_mm = 125, height_mm = 85)

paired <- data.frame(id = rep(1:5, 2), condition = rep(c("Before", "After"), each = 5),
                     value = c(1.1, 1.5, 1.4, 1.8, 1.2, 1.8, 2.0, 1.9, 2.2, 2.1))
paired$condition <- factor(paired$condition, levels = c("Before", "After"))
p2 <- ggplot(paired, aes(condition, value, group = id)) +
  geom_line(colour = "#BBBBBB", linewidth = 0.4) +
  geom_point(aes(colour = condition), size = 1.8) +
  scale_colour_manual(values = c("#0072B2", "#D55E00")) +
  labs(x = NULL, y = "Paired response (a.u.)") + theme_light_chart() + theme(legend.position = "none")
save_figure_r(p2, file.path(out, "A02_paired"), width_mm = 125, height_mm = 85)

trend <- data.frame(x = c(0, 1, 4, 10), y = c(1, 1.3, 1.9, 2.2))
p3 <- ggplot(trend, aes(x, y)) + geom_line(colour = "#009E73", linewidth = 0.6) +
  geom_point(colour = "#009E73", size = 1.7) +
  labs(x = "Time (h)", y = "Response (a.u.)") + theme_light_chart()
p4 <- ggplot(data.frame(x = 1:8, y = c(1, 1.4, 1.2, 1.8, 2.2, 1.9, 2.5, 2.8)), aes(x, y)) +
  geom_point(colour = "#CC79A7", size = 1.7) + labs(x = "Predictor (a.u.)", y = "Outcome (a.u.)") + theme_light_chart()
misaligned <- try(save_figure_r(((p1 | p2) / (p3 | p4)), file.path(out, "A05_negative_nested"),
                              width_mm = 180, height_mm = 135,
                              alignment_options = list(design = matrix(c("a","b","c","d"), 2, byrow = TRUE))), silent = TRUE)
stopifnot(inherits(misaligned, "try-error"))
grid_plot <- (p1 + p2 + p3 + p4 + plot_layout(ncol = 2)) + plot_annotation(tag_levels = "a")
save_figure_r(grid_plot, file.path(out, "A05_grid"), width_mm = 180, height_mm = 135,
              alignment_options = list(design = matrix(c("a","b","c","d"), 2, byrow = TRUE)))
span_plot <- p1 + p2 + p3 + plot_layout(design = "AC\nBC")
save_figure_r(span_plot, file.path(out, "A05_spanning"), width_mm = 180, height_mm = 120,
              alignment_options = list(design = matrix(c("a","c","b","c"), 2, byrow = TRUE)))

zh <- ggplot(trend, aes(x, y)) + geom_line(colour = "#0072B2", linewidth = 0.6) +
  geom_point(colour = "#0072B2", size = 1.8) +
  labs(x = "时间（小时）", y = "响应强度（任意单位）", title = "合成数据：中文与数学符号验证") +
  theme_light_chart(lang = "zh")
save_figure_r(zh, file.path(out, "A08_chinese"), width_mm = 150, height_mm = 100, lang = "zh")
cat("R_ACCEPTANCE_COMPLETE\n")

quit(save = "no", status = 0, runLast = FALSE)
