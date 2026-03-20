# CVRP Solver - Proyecto de Optimización Logística

Este documento describe la resolución y análisis del **Problema de Rutas de Vehículos con Capacidad (CVRP)**, una extensión fundamental del Problema del Viajante de Comercio (TSP) aplicada a la logística industrial.

---

## 1. El Proyecto (Contexto, Objetivo y Resultados)

El proyecto se desarrolla a través de tres componentes clave que definen su propósito:

a.  **Fundamentación Logística**: El problema CVRP consiste en planificar una serie de rutas de entrega que parten de un depósito central para visitar a un conjunto de clientes y satisfacer su demanda, regresando al punto de origen sin exceder la capacidad máxima de cada vehículo y minimizando la distancia total.

b.  **Objetivo del Experimento**: El fin principal es realizar un **Análisis de Escalabilidad**. Se busca identificar el "techo computacional" del solver al incrementar de forma sucesiva el número de clientes, observando cómo el tiempo de resolución crece de forma no lineal (NP-Hard).

c.  **Visualización y Evidencia**: No solo se busca una respuesta numérica; el proyecto genera evidencia visual de cada solución factible, permitiendo verificar que las rutas sean lógicas y que cada nodo sea visitado mediante una gestión eficiente del flujo de carga.

---

## 2. El Escenario de Datos (Casos Ficticios)

Para este estudio se generan datos sintéticos que representan un escenario de distribución urbana estándar:

a.  **Malla Geográfica**: Se utiliza un plano cartesiano de 100x100 unidades de distancia donde los nodos (clientes) aparecen de forma aleatoria.

b.  **El Depósito (Nodo 0)**: Se establece una coordenada central aleatoria que sirve como inicio y fin obligatorio para todos los vehículos. Su demanda es siempre cero.

c.  **Capacidad de Flota**: Cada vehículo posee una capacidad fija de **50 unidades**.

d.  **Demandas de Clientes**: Cada cliente (`id: i`) requiere una carga aleatoria entre **1 y 16 unidades** (un tercio de la capacidad), lo que obliga a la flota a realizar varias rutas separadas cuando la demanda total acumulada de un conjunto de clientes supera las 50 unidades.

e.  **Persistencia Incremental**: Los datos de todos los nodos (coordenadas y demandas) se almacenan en `data/cvrp_nodes.csv`. En cada iteración se reutilizan los nodos previos y solo se generan los faltantes, garantizando continuidad entre ejecuciones.

---

## 3. Metodologías y Tecnologías Aplicadas

La resolución de este caso se basa en técnicas de investigación de operaciones avanzadas:

a.  **Programación Lineal Entera Mixta (MIP)**: Se define el problema mediante variables binarias para decidir recorridos y variables continuas para gestionar la carga acumulada.

b.  **Formulación Miller-Tucker-Zemlin (MTZ)**: Es la metodología usada para la **eliminación de subtours**. Esta técnica garantiza matemáticamente que los vehículos no formen "mini-ciclos" cerrados entre clientes sin pasar primero por el depósito.

c.  **Optimización bajo PuLP/CBC**: Se utiliza el lenguaje de modelado PuLP y el motor de optimización CBC para encontrar la solución óptima del modelo planteado.

d.  **Graficación por Capas (NetworkX/Matplotlib)**: Una metodología de representación de grafos direccionados para superponer las rutas óptimas sobre las coordenadas geográficas de los clientes.

---

## 4. Arquitectura, Implementación y Clasificación de Estados

El script `cvrp_solver.py` se organiza en sus funciones críticas de modelado y un sistema de evaluación de resultados:

a.  **Generación y Persistencia de Datos** (`generate_cvrp_data`)
-   Carga nodos existentes desde `data/cvrp_nodes.csv` y genera solo los faltantes con semilla fija (`seed=42`).
-   Calcula la **Matriz de Distancias Euclidiana** para que el modelo conozca el costo de viajar de cualquier nodo A al B.

b.  **El Núcleo de Modelado** (`solve_cvrp_iteration`)
-   **Variables**:
    -   `x_ij`: 1 si se viaja de `i` a `j`, 0 de lo contrario.
    -   `u_i`: Nivel de carga acumulada al llegar al cliente `i`.
-   **Restricciones de flujo**: Garantizan que entra un vehículo y sale un vehículo por cada cliente.
-   **Restricciones de capacidad**: Impiden que la variable `u_i` supere las 50 unidades acumuladas.

c.  **Renderizado de Solución** (`draw_cvrp_solution`)
-   Extrae las variables `x_ij` activas y crea un objeto `nx.DiGraph`.
-   Diferencia visualmente el depósito (rojo) de los clientes (azul cielo) y dibuja flechas de dirección para las rutas.
-   Incluye reglas de medida en ambos ejes (ticks cada 10 unidades de distancia).

d.  **Orquestador Principal** (`main`)
-   Imprime las características del sistema (SO, procesador, RAM) antes de iniciar el experimento.
-   Ejecuta el bucle incremental (incrementando `num_nodes`). Registra tiempos de ejecución y detiene el proceso automáticamente al detectar un tiempo excesivo o una solución no encontrada.

e.  **Lógica de Clasificación de Estados**
El sistema categoriza el resultado de cada experimento basándose en las reglas del modelo y los límites de ejecución:
-   **Estado: Factible (Óptimo)**: El solver (**CBC**) halla la solución matemática perfecta dentro del límite.
-   **Estado: Factible (Aproximado)**: Se halló una ruta válida, pero el solver agotó el tiempo antes de certificar que fuera la mejor posible (GAP > 2.5%).
-   **Estado: Infactible (Matemático)**: Las restricciones (nodos vs capacidad mínima) hacen que sea estructuralmente imposible de resolver.
-   **Estado: No encontrada (Tiempo Excedido)**: El solver no pudo hallar ninguna ruta válida en el tiempo límite (60 segundos).

---

## 🚀 Guía Rápida de Instalación

```powershell
# 1. Preparar entorno
python -m venv venv
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
.\venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Correr experimento
python cvrp_solver.py
```

---

## 📊 Galería de Resultados del Último Experimento

A continuación se muestra el comportamiento observado durante el análisis:

### Ambiente de Ejecución

```
SO:              Windows 11 (10.0.26200)
Arquitectura:    AMD64
Procesador:      AMD64 Family 25 Model 68 Stepping 1, AuthenticAMD
Python:          3.13.5
```

### Resultados

| Nodos | Tiempo (seg) | Estado |
|-------|--------------|--------|
| 1 | 0.14 | Factible |
| 2 | 0.08 | Factible |
| 3 | 0.09 | Factible |
| 4 | 0.10 | Factible |
| 5 | 0.22 | Factible |
| 6 | 0.32 | Factible |
| 7 | 1.14 | Factible |
| 8 | 2.07 | Factible |
| 9 | 10.06 | Factible |
| 10 | 17.64 | Factible |
| 11 | 33.51 | Factible |
| 12 | 60.04 | Factible |
| 13 | 60.16 | Factible |
| 14 | 61.82 | Factible |
| 15 | 65.78 | Factible |
| 16 | 76.65 | Factible |
| 17 | 59.71 | Factible |
| 19 | 59.11 | Factible |
| 20 | 59.25 | Factible |
| 21 | 58.67 | Factible |
| 22 | 58.66 | Factible |
| 23 | 58.39 | Factible |
| 24 | 58.14 | Factible |
| 34 | 53.79 | Factible |
| 37 | 52.15 | Factible |
| 38 | --- | No encontrada |

> [!NOTE]
> **Observación del Experimento**: Las pruebas se extendieron hasta los **160 nodos**. Sin embargo, a partir del **nodo 38**, el solver dejó de proporcionar soluciones certificadas como "Óptimo" debido a la complejidad exponencial del problema bajo restricciones tan estrictas (Capacidad 50 y flota mínima). Dado que el objetivo era el análisis de escalabilidad de soluciones exactas, el proceso se detuvo manualmente al detectar esta pérdida de precisión sistemática.

![Análisis de Escalabilidad](plots/scalability_chart.png)
![Análisis de Escalabilidad (Escala Logarítmica)](plots/scalability_chart_log.png)

#### Galería de Soluciones
![Solución para 1 nodos](plots/cvrp_solution_1_nodes.png)
![Solución para 2 nodos](plots/cvrp_solution_2_nodes.png)
![Solución para 3 nodos](plots/cvrp_solution_3_nodes.png)
![Solución para 4 nodos](plots/cvrp_solution_4_nodes.png)
![Solución para 5 nodos](plots/cvrp_solution_5_nodes.png)
![Solución para 6 nodos](plots/cvrp_solution_6_nodes.png)
![Solución para 7 nodos](plots/cvrp_solution_7_nodes.png)
![Solución para 8 nodos](plots/cvrp_solution_8_nodes.png)
![Solución para 9 nodos](plots/cvrp_solution_9_nodes.png)
![Solución para 10 nodos](plots/cvrp_solution_10_nodes.png)
![Solución para 11 nodos](plots/cvrp_solution_11_nodes.png)
![Solución para 12 nodos](plots/cvrp_solution_12_nodes.png)
![Solución para 13 nodos](plots/cvrp_solution_13_nodes.png)
![Solución para 14 nodos](plots/cvrp_solution_14_nodes.png)
![Solución para 15 nodos](plots/cvrp_solution_15_nodes.png)
![Solución para 16 nodos](plots/cvrp_solution_16_nodes.png)
![Solución para 17 nodos](plots/cvrp_solution_17_nodes.png)
![Solución para 19 nodos](plots/cvrp_solution_19_nodes.png)
![Solución para 20 nodos](plots/cvrp_solution_20_nodes.png)
![Solución para 21 nodos](plots/cvrp_solution_21_nodes.png)
![Solución para 22 nodos](plots/cvrp_solution_22_nodes.png)
![Solución para 23 nodos](plots/cvrp_solution_23_nodes.png)
![Solución para 24 nodos](plots/cvrp_solution_24_nodes.png)
![Solución para 34 nodos](plots/cvrp_solution_34_nodes.png)
![Solución para 37 nodos](plots/cvrp_solution_37_nodes.png)
