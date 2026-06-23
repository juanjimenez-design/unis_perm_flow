rm(list = ls())
library(survival)
library(survminer)
library(dplyr)
library(tidyr)
library(ggplot2)
library(broom)
# Cargar datos parquet
library(arrow)
df <- read_parquet("../data/03_primary/unis_estaca_survival.parquet")
#df = na.omit(df[, c("month", "di", "periodo_inicial", "programa", "mes_gregoriano")])
df = df %>% 
  filter(!is.na(periodo_inicial)) 
# Cuando el mes sea 16 y di sea 1, es decir, cuando el evento de interés ocurra en el mes 16,
# di tiene que ser cero
df = df %>% mutate(di = ifelse(month == 16 & di == 1, 0, di))

# 1. Ajustar el modelo general de Kaplan-Meier
km_fit <- survfit(Surv(month, di) ~ programa, data = df)

# 2. Extraer la tabla de supervivencia detallada
# Creamos un data.frame limpio con el tiempo, la supervivencia y el programa
surv_puntos <- data.frame(
  time      = km_fit$time,
  surv      = km_fit$surv,
  # km_fit$strata nos dice cuántas filas le corresponden a cada programa
  programa  = rep(names(km_fit$strata), km_fit$strata)
) %>%
  # Limpiamos el nombre para quitar el prefijo "programa="
  mutate(programa = stringr::str_remove(programa, "programa="))

# 3. Pivotar los datos para tener los programas como columnas y el tiempo como filas
# Rellenamos los valores faltantes (NA) con el último valor conocido (foward fill)
matriz_surv <- surv_puntos %>%
  #mutate(programa = stringr::str_remove(strata, "programa=")) %>%
  select(time, programa, surv) %>%
  distinct(time, programa, .keep_all = TRUE) %>%
  pivot_wider(names_from = programa, values_from = surv) %>%
  arrange(time) %>%
  tidyr::fill(everything(), .direction = "down") %>%
  tidyr::fill(everything(), .direction = "up") 

  #filter(!complete.cases(.)) # Asegurar que no queden baches iniciales si entran en tiempos distintos

# Quitamos la columna de tiempo para quedarnos solo con las curvas
matriz_para_cluster <- t(matriz_surv[, -1])

# 1. Calcular la matriz de distancias Euclidianas
distancias <- dist(matriz_para_cluster, method = "euclidean")

# 2. Aplicar clustering jerárquico usando el método de Ward 
# (Ward minimiza la varianza dentro de cada cluster, ideal para grupos homogéneos)
cluster_programas <- hclust(distancias, method = "ward.D2")

# 3. Graficar el Dendrograma
plot(cluster_programas, 
     main = "Clusterización de Programas por Similitud de Supervivencia",
     sub = "Método de Ward / Distancia Euclidiana",
     xlab = "Programas", ylab = "Distancia (Disimilitud)")

# 4. Dibujar rectángulos para identificar visualmente tus grupos (ej: 3 clusters)
rect.hclust(cluster_programas, k = 3, border = "red")







