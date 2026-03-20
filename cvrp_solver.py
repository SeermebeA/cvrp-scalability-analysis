"""
CVRP Solver - Experimento Académico de Optimización
--------------------------------------------------
Este script resuelve el Problema de Rutas de Vehículos con Capacidad (CVRP)
de forma incremental, analizando la escalabilidad y generando visualizaciones.

Requisitos: pulp, networkx, matplotlib
"""

import math
import random
import time
import pulp
import networkx as nx
import matplotlib.pyplot as plt
import os

# CONFIGURACIÓN: Carpeta para guardar los resultados visuales
PLOTS_DIR = 'plots'
if not os.path.exists(PLOTS_DIR):
    os.makedirs(PLOTS_DIR)

def generate_cvrp_data(num_nodes, capacity, seed=42):
    """
    Genera un conjunto de datos aleatorios para el problema CVRP.
    
    Args:
        num_nodes (int): Cantidad total de nodos (incluyendo el depósito).
        capacity (int): Capacidad máxima de carga por vehículo.
        seed (int): Semilla aleatoria para reproducibilidad.
        
    Returns:
        tuple: (Lista de nodos con coord x,y y demanda, Matriz de distancias Euclidiana)
    """
    random.seed(seed)
    
    # El nodo 0 es siempre el depósito (depot), con demanda 0
    nodes = [{'id': 0, 'x': random.uniform(0, 100), 'y': random.uniform(0, 100), 'demand': 0}]
    
    # Resto de los nodos representas clientes con demandas aleatorias entre 1 y capacity/3
    for i in range(1, num_nodes):
        demand = random.randint(1, max(1, capacity // 3))
        nodes.append({'id': i, 'x': random.uniform(0, 100), 'y': random.uniform(0, 100), 'demand': demand})
        
    # Calcular matriz de distancias Euclidiana entre todos los pares de nodos (i, j)
    distances = {}
    for i in range(num_nodes):
        for j in range(num_nodes):
            if i != j:
                dx = nodes[i]['x'] - nodes[j]['x']
                dy = nodes[i]['y'] - nodes[j]['y']
                distances[(i, j)] = math.sqrt(dx**2 + dy**2)
            else:
                distances[(i, j)] = 0.0
                
    return nodes, distances

def draw_cvrp_solution(nodes, x_vars, num_nodes):
    """
    Genera una representación gráfica de las rutas encontradas y la guarda como PNG.
    
    Args:
        nodes (list): Datos de los nodos (id, x, y, demand).
        x_vars (dict): Diccionario de variables de decisión de PuLP con sus valores.
        num_nodes (int): Número de nodos para etiquetar el archivo de salida.
    """
    G = nx.DiGraph()
    
    # Mapear las posiciones reales (x, y) de cada nodo para el dibujo del grafo
    pos = {n['id']: (n['x'], n['y']) for n in nodes}
    
    # Añadir nodos al grafo de NetworkX
    G.add_nodes_from(pos.keys())
    
    # Extraer las aristas (rutas) donde la variable binaria 'x' es igual a 1
    edges = []
    for (i, j), var in x_vars.items():
        if var.varValue is not None and var.varValue > 0.5:
            edges.append((i, j))
    
    G.add_edges_from(edges)
    
    plt.figure(figsize=(10, 8))
    
    # Dibujar nodos: El depósito (0) se pinta de Rojo, los clientes de Azul Cielo
    node_colors = ['red' if i == 0 else 'skyblue' for i in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=500)
    nx.draw_networkx_labels(G, pos, font_size=10)
    
    # Dibujar las rutas con flechas para indicar el sentido del vehículo
    nx.draw_networkx_edges(G, pos, edgelist=edges, edge_color='darkblue', 
                           arrows=True, arrowsize=15, width=1.5)
    
    plt.title(f"Solución CVRP Óptima/Factible - {num_nodes} Nodos")
    plt.xlabel("Coordenada X")
    plt.ylabel("Coordenada Y")
    plt.grid(True, linestyle='--', alpha=0.6)
    
    # Guardar en la carpeta de resultados
    plt.savefig(f"{PLOTS_DIR}/cvrp_solution_{num_nodes}_nodes.png")
    plt.close()

def solve_cvrp_iteration(num_nodes, capacity=100, time_limit=60):
    """
    Crea, modela y resuelve una instancia específica de CVRP usando programación lineal.
    Usa la formulación de Dantzig-Fulkerson-Johnson simplificada con restricciones MTZ.
    
    Args:
        num_nodes (int): Cantidad de nodos a resolver.
        capacity (int): Capacidad de los vehículos.
        time_limit (int): Segundos máximos permitidos antes de abortar.
        
    Returns:
        tuple: (Estado de la solución, Tiempo de ejecución en segundos)
    """
    start_time = time.perf_counter()
    nodes, distances = generate_cvrp_data(num_nodes, capacity, seed=num_nodes)
    
    N = range(num_nodes)  # Conjunto de todos los nodos (incluyendo el depósito)
    C = range(1, num_nodes) # Conjunto de clientes (nodos sin el depósito)
    
    # Cálculo aproximado de vehículos necesarios (total demanda / capacidad + margen)
    total_demand = sum(n['demand'] for n in nodes)
    num_vehicles = math.ceil(total_demand / capacity) + 2 
    
    # Definición del problema: Minimizar costo (distancias)
    model = pulp.LpProblem("Capacitated_VRP", pulp.LpMinimize)
    
    # VARIABLE DE DECISIÓN: x_ij = 1 si un vehículo viaja del nodo i al nodo j
    x = {}
    for i in N:
        for j in N:
            if i != j:
                x[(i, j)] = pulp.LpVariable(f"x_{i}_{j}", cat=pulp.LpBinary)
                
    # VARIABLE AUXILIAR (MTZ): u_i representa la carga acumulada en el nodo i
    # Ayuda a evitar subtours (ciclos que no pasan por el depósito)
    u = {}
    for i in C:
        u[i] = pulp.LpVariable(f"u_{i}", lowBound=nodes[i]['demand'], upBound=capacity, cat=pulp.LpContinuous)
        
    # FUNCIÓN OBJETIVO: Minimizar el sumatorio de distancias recorridas
    model += pulp.lpSum(distances[(i, j)] * x[(i, j)] for i in N for j in N if i != j)
    
    # RESTRICCIONES:
    # 1. Conservación de flujo: Cada cliente recibe exactamente UNA visita
    for j in C:
        model += pulp.lpSum(x[(i, j)] for i in N if i != j) == 1
    
    # 2. Conservación de flujo: Cada cliente debe ser abandonado UNA vez
    for i in C:
        model += pulp.lpSum(x[(i, j)] for j in N if i != j) == 1
        
    # 3. Restricciones del Depósito: No más de 'K' vehículos pueden salir y entrar
    model += pulp.lpSum(x[(0, j)] for j in C) <= num_vehicles
    model += pulp.lpSum(x[(i, 0)] for i in C) <= num_vehicles
    
    # Obligamos a que entren tantos vehículos como los que salieron
    model += pulp.lpSum(x[(0, j)] for j in C) == pulp.lpSum(x[(i, 0)] for i in C)
    
    # 4. ELIMINACIÓN DE SUBTOURS (Formulación Miller-Tucker-Zemlin)
    # Si x_ij = 1, entonces u_j debe ser al menos u_i + demanda_j.
    # Esto rompe ciclos cerrados que no involucren al nodo 0 (depósito).
    for i in C:
        for j in C:
            if i != j:
                model += u[i] - u[j] + capacity * x[(i, j)] <= capacity - nodes[j]['demand']

    # RESOLUCIÓN usando el solver CBC por defecto (incluido en PuLP)
    solver = pulp.PULP_CBC_CMD(timeLimit=time_limit, msg=False)
    model.solve(solver)
    
    end_time = time.perf_counter()
    exec_time_s = end_time - start_time
    
    status_label = pulp.LpStatus[model.status]
    has_solution = False
    
    # Verificar si el solver produjo algún resultado factible (incumbente)
    try:
        if any(x[key].varValue is not None and x[key].varValue > 0.5 for key in x):
            has_solution = True
    except Exception:
        pass

    # Si la solución es óptima o al menos factible, graficamos el resultado
    if status_label == "Optimal" or (has_solution and getattr(model, "objective", None) is not None):
        draw_cvrp_solution(nodes, x, num_nodes)
        return "Factible", exec_time_s
    else:
        return "No encontrada", exec_time_s

def main():
    """Función de entrada que ejecuta el experimento incrementalmente."""
    print("=================================================================")
    print(" EXPERIMENTO ACADÉMICO: Capacitated Vehicle Routing Problem")
    print("=================================================================")
    
    # Tiempo límite por cada instancia de resolución (en segundos)
    time_limit = 60
    
    # Iniciamos con 10 nodos y escalamos hasta 50
    for num_nodes in range(10, 51):
        status, exec_time = solve_cvrp_iteration(num_nodes=num_nodes, time_limit=time_limit)
        
        # Mostramos resultados en tiempo real
        print(f"#nodos: {num_nodes} --> Tiempo: {exec_time:.2f} segundos, Solución: {status}", flush=True)
        
        # Si el problema deja de ser resoluble o toma demasiado tiempo, detenemos el experimento
        if status == "No encontrada" or exec_time > (time_limit + 5):
            print("=================================================================")
            print("FIN DEL EXPERIMENTO: Límite de complejidad alcanzado.")
            break

if __name__ == "__main__":
    main()
