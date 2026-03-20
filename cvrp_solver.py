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
import csv
import platform

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# CONFIGURACIÓN: Carpetas para guardar resultados
PLOTS_DIR = 'plots'
if not os.path.exists(PLOTS_DIR):
    os.makedirs(PLOTS_DIR)

DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def generate_cvrp_data(num_nodes, capacity, seed=42):
    """
    Genera o carga un conjunto de datos persistidos para el problema CVRP.
    En cada iteración se reutilizan los nodos anteriores y solo se generan los faltantes,
    garantizando continuidad incremental entre ejecuciones.
    
    Args:
        num_nodes (int): Cantidad total de nodos (incluyendo el depósito).
        capacity (int): Capacidad máxima de carga por vehículo.
        seed (int): Semilla aleatoria para reproducibilidad.
        
    Returns:
        tuple: (Lista de nodos con coord x,y y demanda, Matriz de distancias Euclidiana)
    """
    file_path = os.path.join(DATA_DIR, 'cvrp_nodes.csv')
    nodes = []

    # 1. Intentar cargar nodos persistidos desde el CSV
    if os.path.exists(file_path):
        with open(file_path, mode='r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                nodes.append({
                    'id': int(row['id']),
                    'x': float(row['x']),
                    'y': float(row['y']),
                    'demand': int(row['demand'])
                })

    # 2. Si necesitamos más nodos de los que tenemos, generar solo los faltantes
    if len(nodes) < num_nodes:
        # Inicializar la semilla y avanzar la secuencia aleatoria
        # hasta el punto correcto para mantener consistencia
        random.seed(seed)
        # Reproducir la secuencia completa para los nodos que ya existen
        for i in range(len(nodes)):
            random.uniform(0, 100)  # x
            random.uniform(0, 100)  # y
            if i > 0:
                random.randint(1, max(1, capacity // 3))  # demand

        # Generar los nodos faltantes desde donde quedó la secuencia
        for i in range(len(nodes), num_nodes):
            x = random.uniform(0, 100)
            y = random.uniform(0, 100)
            demand = 0 if i == 0 else random.randint(1, max(1, capacity // 3))
            nodes.append({'id': i, 'x': x, 'y': y, 'demand': demand})

        # 3. Persistir el conjunto completo actualizado en disco
        with open(file_path, mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'x', 'y', 'demand'])
            writer.writeheader()
            writer.writerows(nodes)

    # Usar solo la cantidad de nodos solicitada para esta iteración
    active_nodes = nodes[:num_nodes]

    # Calcular matriz de distancias Euclidiana entre todos los pares de nodos (i, j)
    distances = {}
    for i in range(num_nodes):
        for j in range(num_nodes):
            if i != j:
                dx = active_nodes[i]['x'] - active_nodes[j]['x']
                dy = active_nodes[i]['y'] - active_nodes[j]['y']
                distances[(i, j)] = math.sqrt(dx**2 + dy**2)
            else:
                distances[(i, j)] = 0.0
                
    return active_nodes, distances

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
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # Dibujar nodos: El depósito (0) se pinta de Rojo, los clientes de Azul Cielo
    node_colors = ['red' if i == 0 else 'skyblue' for i in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=500, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=10, ax=ax)
    
    # Dibujar las rutas con flechas para indicar el sentido del vehículo
    nx.draw_networkx_edges(G, pos, edgelist=edges, edge_color='darkblue', 
                           arrows=True, arrowsize=15, width=1.5, ax=ax)
    
    # Activar ejes con reglas de medida (ticks cada 10 unidades)
    ax.tick_params(left=True, bottom=True, labelleft=True, labelbottom=True)
    ax.set_xticks(range(0, 101, 10))
    ax.set_yticks(range(0, 101, 10))
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, 105)
    
    ax.set_title(f"Solución CVRP Óptima/Factible - {num_nodes} Nodos")
    ax.set_xlabel("Coordenada X (unidades de distancia)")
    ax.set_ylabel("Coordenada Y (unidades de distancia)")
    ax.grid(True, linestyle='--', alpha=0.6)
    
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
    nodes, distances = generate_cvrp_data(num_nodes, capacity, seed=42)
    
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

def print_system_info():
    """Muestra las características del ambiente de ejecución."""
    print("-----------------------------------------------------------------")
    print(" INFORMACIÓN DEL SISTEMA")
    print("-----------------------------------------------------------------")
    print(f"  SO:              {platform.system()} {platform.release()} ({platform.version()})")
    print(f"  Arquitectura:    {platform.machine()}")
    print(f"  Procesador:      {platform.processor()}")
    print(f"  Python:          {platform.python_version()}")
    if HAS_PSUTIL:
        cpu_freq = psutil.cpu_freq()
        ram = psutil.virtual_memory()
        print(f"  Núcleos físicos: {psutil.cpu_count(logical=False)}")
        print(f"  Núcleos lógicos: {psutil.cpu_count(logical=True)}")
        if cpu_freq:
            print(f"  Frecuencia CPU:  {cpu_freq.current:.0f} MHz (max: {cpu_freq.max:.0f} MHz)")
        print(f"  RAM total:       {ram.total / (1024**3):.2f} GB")
        print(f"  RAM disponible:  {ram.available / (1024**3):.2f} GB")
    else:
        print("  (Instale 'psutil' para ver detalles de CPU/RAM: pip install psutil)")
    print("-----------------------------------------------------------------")

def main():
    """Función de entrada que ejecuta el experimento incrementalmente."""
    print("=================================================================")
    print(" EXPERIMENTO ACADÉMICO: Capacitated Vehicle Routing Problem")
    print("=================================================================")
    print_system_info()
    
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
