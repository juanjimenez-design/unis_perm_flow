rm(list = ls())
# Librarías
setwd("G:/Unidades compartidas/Alianzas/3. Data/UNIS/unis-perm-flow/notebooks")
library(survival)
library(survminer)
library(ggplot2)
library(dplyr)
library(broom)
# Cargar datos parquet
library(arrow)
#df <- read_parquet("../data/03_primary/unis_estaca_survival.parquet")
df = read_parquet('../data/03_Primary/unis_estados_calac_survival.parquet/2026-06-23T16.55.34.059Z/unis_estados_calac_survival.parquet')
#df = na.omit(df[, c("month", "di", "periodo_inicial", "programa", "mes_gregoriano")])

  

# Limpieza de datos ----------------------------------------------------

# Cuando el mes sea 16 y di sea 1, es decir, cuando el evento de interés ocurra en el mes 16,
# di tiene que ser cero
#df = df %>% mutate(di = ifelse(month == 16 & di == 1, 0, di))

# Preparar datos.Se convierten los datos categóricos a factores y se establece un nivel de referencia para cada uno de ellos.
df$periodo_inicial = as.factor(df$periodo_inicial)
df$periodo_inicial = relevel(df$periodo_inicial, ref = "9243") 
df$programa = as.factor(df$programa)
df$programa = relevel(df$programa, ref = "marketing digital")


# Kaplan Meier ------------------------------------------------------------

## Cohorte Periodo inicial
km_fit <- survfit(Surv(month,di) ~ periodo_inicial , data = df) 
# Graficar Kaplan meier
ggsurvplot(km_fit, data = df, 
           pval = TRUE, 
           conf.int = F, 
           risk.table = TRUE, 
           risk.table.col = "strata", 
           linetype = "strata", 
           surv.median.line = "hv", 
           ggtheme = theme_bw(), 
          # palette = c("#E7B800", "#2E9FDF", "#FC4E07", "#00AFBB", "#E7B800", "#2E9FDF", "#FC4E07", "#00AFBB"),
           title = "Curvas de supervivencia por periodo inicial y programa",
           xlab = "Meses",
           ylab = "Probabilidad de supervivencia")


## Programa 
km_fit <- survfit(Surv(month,di) ~ programa , data = df) 
# Graficar Kaplan meier
ggsurvplot(km_fit, data = df, 
           pval = TRUE, 
           conf.int = F, 
           risk.table = TRUE, 
           risk.table.col = "strata", 
           linetype = "strata", 
           surv.median.line = "hv", 
           ggtheme = theme_bw(), 
           # palette = c("#E7B800", "#2E9FDF", "#FC4E07", "#00AFBB", "#E7B800", "#2E9FDF", "#FC4E07", "#00AFBB"),
           title = "Curvas de supervivencia por periodo inicial y programa",
           xlab = "Meses",
           ylab = "Probabilidad de supervivencia")



# Ajuste del modelo boxcox ------------------------------------------------

modelo.coxph = coxph(Surv(month, di) ~ periodo_inicial + programa , data = df)

## Stepwise 
modelAll.coxph = coxph(Surv(month, di) ~ periodo_inicial + programa , data = df)
result.stepwise = step(modelAll.coxph, direction = "backward", scope = list(upper = ~ periodo_inicial + programa , lower = ~ programa))

## Best model
best_model = result.stepwise
summary(best_model)

## Forest Plot para analizar el efecto de os programas sobre la sobrevivencia
# 3. Generar el gráfico ggforest
ggforest(best_model, 
         data = df, 
         main = "Hazard Ratios para el Modelo de Cox",
         cpositions = c(0.02, 0.22, 0.4), # Ajusta columnas si los nombres son largos
         fontsize = 0.8,                  # Tamaño de la fuente
         refLabel = "Referencia",         # Etiqueta para la categoría base
         noDigits = 2)


termplot(best_model, se = TRUE, terms = "programa", ylabs = "log hazard", col.term = "blue", col.se = "red", main = "Efecto de los programas sobre la sobrevivencia")


## Baseline hazard function
h0 = basehaz(best_model, centered = FALSE)
ggplot(h0, aes(x = time, y = hazard)) + 
  geom_line(color = "blue", linewidth = 1) + 
  labs(title = "Función de riesgo acumulada", x = "Tiempo (meses)", y = "Riesgo acumulado") + 
  theme_minimal() +
  theme(plot.title = element_text(hjust = 0.5))


## Hazard function para cada programa para el modelo cuya única variable explicativa es programa.
### Hi(t) = h0(t) * exp(beta * programa)

h0 = basehaz(best_model, centered = FALSE)
# Obtener los coeficientes del modelo
coef_model = coef(best_model)
# Calcular la función de riesgo para cada programa
programas = levels(df$programa)
hazard_programas = data.frame(time = h0$time)
hazard_programas[["marketing digital"]] = h0$hazard * exp(0)  # Programa de referencia
for (prog in programas[-1]) {
  beta_prog = coef_model[paste0("programa", prog)]
  hazard_programas[[prog]] = h0$hazard * exp(beta_prog)
}
## Graaficar la función de riesgo para cada programa
library(tidyr)
hazard_programas_long = hazard_programas %>%
                        pivot_longer(cols = -time, names_to = "programa", values_to = "hazard")
ggplot(hazard_programas_long, aes(x = time, y = hazard, colour = programa)) +    
  geom_line(linewidth = 1) +
  labs(title = "Función de riesgo acumuada por programa", x = "Tiempo (meses)", y = "Riesgo acumulado") +
  theme_minimal() +
  theme(plot.title = element_text(hjust = 0.5)) +
  scale_color_brewer(palette = "Set1")



## Predicciones de supervivencia para cada programa
new_data = data.frame(programa = levels(df$programa))      # Nivel de referencia
surv_fit = survfit(best_model, newdata = new_data)

ggsurvplot(surv_fit, data = new_data,
           pval = TRUE,
           conf.int = TRUE,
           risk.table = FALSE,
           risk.table.col = "strata",
           linetype = "strata",
           surv.median.line = "hv",
           ggtheme = theme_bw(),
           title = "Curvas de supervivencia por programa",
           xlab = "Meses",
           ylab = "Probabilidad de supervivencia")




# Model Diagnostic --------------------------------------------------------

## Bondad de Ajuste visualmente 
## Kaplan Meier vs coxph. Comparación  en un grilla de gráficos


# 1. Ajustar y extraer datos de Kaplan-Meier
km_fit = survfit(Surv(month, di) ~ programa , data = df)

km_data <- tidy(km_fit) %>%
  # broom guarda la variable en una columna llamada 'strata' (ej: "programa=A")
  # Limpiamos el texto para quedarnos solo con el nombre del programa
  mutate(
    Programa = stringr::str_remove(strata, "programa="),
    Modelo = "Kaplan-Meier"
  ) %>%
  select(time, estimate, Modelo, Programa)

# 2. Extraer datos de la predicción de Cox
# Es vital que 'new_data' contenga la columna 'programa' con los mismos niveles
pred_fit = survfit(best_model, newdata = new_data)
cox_data <- tidy(pred_fit)
colnames(cox_data) <- c("time", "n.risk", "n.event", "n.censor", programas)
# Pivot 
cox_data = cox_data %>% select(time,programas ) %>%
  pivot_longer(cols = programas, names_to = "Programa", values_to = "estimate") %>%
  mutate(
  Modelo = "Cox PH"
) %>%
  select(time, estimate, Modelo, Programa)
  
# 3. Combinar ambos sets de datos limpios
df_grafico <- bind_rows(km_data, cox_data)


# 4. El Gráfico final separado por paneles (facets)
ggplot(df_grafico, aes(x = time, y = estimate, color = Modelo, linetype = Modelo)) +
  geom_step(linewidth = 1) + 
  facet_wrap(~ Programa) + # Aquí ocurre la magia de la separación
  scale_color_manual(values = c("Kaplan-Meier" = "#1f77b4", "Cox PH" = "#e74c3c")) +
  scale_linetype_manual(values = c("Kaplan-Meier" = "solid", "Cox PH" = "dashed")) +
  labs(
    title = "Comparación de Supervivencia por Programa",
    subtitle = "Kaplan-Meier (Real) vs. Cox PH (Modelo)",
    x = "Meses",
    y = "Probabilidad de supervivencia",
    color = "Modelo",
    linetype = "Modelo"
  ) +
  theme_minimal(base_size = 14) +
  theme(
    legend.position = "top",
    strip.text = element_text(face = "bold", size = 12)
  )


## Martingale Residuals
rr.0 = residuals(best_model, type = "martingale")
plot(df$programa, rr.0, 
     xlab = "Programa", 
     ylab = "Residuos Martingale",
     main = "Residuos Martingale vs Programa")


## Case Deletion Residuals
resid.dfbeta = residuals(best_model, type = "dfbetas")

n.obs = length(df$di)
index = 1:n.obs
plot(resid.dfbeta[,1] ~ index, 
     xlab = "Residuos DFBETA ", 
     ylab = "Índice de Observación", 
     main = "Residuos DFBETA vs Índice de Observación",
     pch = 19,
     type = 'h')
abline(h = 0, col = "red", lty = 2)
#identify(resid.dfbeta[,1] ~ index)


## Residuals de Schoenfeld
residuals_schoenfeld = cox.zph(best_model, transform = "rank")

## Graficar los residuos de Schoenfeld
plot(residuals_schoenfeld, main = "Residuos de Schoenfeld",
     xlab = "Tiempo", ylab = "Residuos de Schoenfeld", col = "blue", lwd = 2)
print(residuals_schoenfeld)




# Proceso Final -----------------------------------------------------------

# Preparar datos.Se convierten los datos categóricos a factores y se establece un nivel de referencia para cada uno de ellos.
df = read_parquet('../data/03_Primary/unis_estados_calac_survival.parquet/2026-06-23T16.55.34.059Z/unis_estados_calac_survival.parquet')
df$periodo_inicial = as.factor(df$periodo_inicial)
df$periodo_inicial = relevel(df$periodo_inicial, ref = "9243") 
df$programa = as.factor(df$programa)
df$programa = relevel(df$programa, ref = "marketing digital")

best_model = coxph(Surv(month, di) ~ programa , data = df)
pred_individual <- survfit(best_model, newdata = df)                                    
obtener_p_mes <- function(fit, t_objetivo) {
  # fit$time y fit$surv contienen los pasos de la escalera.
  # summary(fit, times = ...) nos da la supervivencia exacta en ese tiempo (o el inmediato anterior)
  res <- summary(fit, times = t_objetivo, extend = TRUE)
  return(res$surv) # Retorna una matriz de dimensiones [tiempo, individuos]
}          

matriz_probabilidades <- obtener_p_mes(pred_individual, meses_evaluar)
df_probabilidades <- df %>% 
  # Nos quedamos con tus variables de identificación y la variable predictora del modelo
  select(identificacion, periodo_inicial, nivel, programa, month, di) %>%
  # Añadimos la matriz de probabilidades como una lista por cada estudiante
  mutate(p_sobrevivir = as.data.frame(matriz_probabilidades) %>% as.list()) %>%
  # Expandimos el dataset para que cada estudiante tenga sus filas por mes
  unnest(p_sobrevivir) %>%
  # Agregamos la columna que identifica a qué mes corresponde cada probabilidad
  group_by(identificacion,periodo_inicial, programa,month, di) %>% 
  mutate(mes = meses_evaluar) %>%
  ungroup()





# Proyecciones ------------------------------------------------------------

library(purrr)

# 1. Definir la cuadrícula de meses que quieres estimar (ej. del mes 1 al mes máximo en tus datos)
max_mes <- 16 #max(df$month, na.rm = TRUE)
meses_evaluar <- 1:max_mes

# 2. Obtener la predicción de supervivencia para CADA estudiante único en el dataset
# 'survfit' con el dataset original calcula la curva individualizada para cada fila
pred_individual <- survfit(best_model, newdata = df)

# 3. Extraer las probabilidades para los meses exactos que definimos
# Creamos una función que interpola o busca la supervivencia al mes 't' para cada individuo
obtener_p_mes <- function(fit, t_objetivo) {
  # fit$time y fit$surv contienen los pasos de la escalera.
  # summary(fit, times = ...) nos da la supervivencia exacta en ese tiempo (o el inmediato anterior)
  res <- summary(fit, times = t_objetivo, extend = TRUE)
  return(res$surv) # Retorna una matriz de dimensiones [tiempo, individuos]
}

# Generamos la matriz de probabilidades (Filas: Meses, Columnas: Estudiantes)
matriz_probabilidades <- obtener_p_mes(pred_individual, meses_evaluar)

# Sumar las filas con apply para obtener el número estimado de estudiantes sobrevivientes
apply(matriz_probabilidades, 1, sum)

# 4. Construir el dataset final con las llaves y las probabilidades expandidas por mes
df_probabilidades <- df %>% 
  # Nos quedamos con tus variables de identificación y la variable predictora del modelo
  select(identificacion, periodo_inicial, nivel, programa, month, di) %>%
  # Añadimos la matriz de probabilidades como una lista por cada estudiante
  mutate(p_sobrevivir = as.data.frame(matriz_probabilidades) %>% as.list()) %>%
  # Expandimos el dataset para que cada estudiante tenga sus filas por mes
  unnest(p_sobrevivir) %>%
  # Agregamos la columna que identifica a qué mes corresponde cada probabilidad
  group_by(identificacion,periodo_inicial, programa,month, di) %>% 
  mutate(mes = meses_evaluar) %>%
  ungroup()


# Proyección con respecto a ventas ----------------------------------------

## Nuevos ingresos (Entregados por ventas)
nuevos_estudiantes <- data.frame(
  programa = c("marketing digital", "administracion financiera"), 
  n_inicial = c(150, 120) # Puedes cambiar estos números según tus metas de matrícula
)

# Creamos un set de datos único con los programas para los que queremos predecir
programas_unicos <- data.frame(programa = nuevos_estudiantes$programa)
max_meses <- max(df$month, na.rm = TRUE) # Máximo tiempo registrado en tus datos

# Obtenemos la predicción del modelo de Cox para estos programas
pred_cox <- survfit(best_model, newdata = programas_unicos)

# Extraemos las probabilidades mes a mes para cada programa
# summary(..., times) nos asegura una fila por cada mes del 1 al máximo
tabla_superv_base <- data.frame(
  mes = rep(1:max_meses, each = nrow(programas_unicos)),
  programa = rep(programas_unicos$programa, times = max_meses),
  # summary devuelve una matriz de [meses, programas], la aplanamos a vector
  p_sobrevivir = as.vector(t(summary(pred_cox, times = 1:max_meses, extend = TRUE)$surv))
)


# 3. CALCULAR LA TABLA DE VIDA PROYECTADA (Totales Esperados)

tabla_vida_nuevos <- nuevos_estudiantes %>%
  # Unimos los estudiantes iniciales con sus respectivas probabilidades por mes
  left_join(tabla_superv_base, by = "programa") %>%
  mutate(
    # Tu fórmula: n * S(t) es el valor esperado de la población activa
    estudiantes_esperados_activos = n_inicial * p_sobrevivir,
    # Redondeamos para tener personas enteras en los reportes de planeación
    estudiantes_esperados_redond = round(estudiantes_esperados_activos),
    # Opcional: cuántos alumnos habrán desertado acumulados a ese mes
    desertores_acumulados_esperados = n_inicial - estudiantes_esperados_redond
  ) %>%
  select(programa, mes, n_inicial, p_sobrevivir, estudiantes_esperados_redond, desertores_acumulados_esperados)


# Visualización de las proyecciones
print(tabla_vida_nuevos)


summary(best_model)




