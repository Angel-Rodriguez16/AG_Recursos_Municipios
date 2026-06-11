"""
Autor: Ángel Roberto Rodríguez Miranda
Materia: Algoritmos Geneticos evolutivos.
PROYECTO DE ORDINARIO: IMPLEMENTACIÓN DE UN AG PARA LA ASIGNACIÓN DE RECURSOS A MUNICIPIOS 
SEGUN SU NIVEL DE VULNERABILIDAD DE RIESGOS.

Requerimientos: 
- Representación binaria o entera, gen = municipio.
- Función de adaptación que integre >=2 variables del dataset (Mayor vulnerabilidad = mayor peso)
  penalizar soluciones que excedan el límite de recursos, preferencia adicional a municipios sin ARM
- Comparar 2 tasas distintas de mutación y reportar efecto sobre la convergencia.
Objetivo: Encontrar la distribución más optima de MXN $10,000,000.00 entre los 268 municipios.
Restricciones: No se debe exceder del presupuesto
"""
#Importamos las librerías
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
#Leer csv
data = pd.read_csv("municipios_occidente_riesgo_CENAPRED.csv")

#Conversión de grados a Numeros, Muy bajo = 1 y Muy alto = 5
def grado_a_numero(grado):
     return {'Muy bajo': 1, 'Bajo': 2, 'Medio': 3, 'Alto': 4, 'Muy alto': 5}[grado]

data['zona_sismica_CFE'] = data['zona_sismica_CFE'].map({'A': 1, 'B': 2, 'C': 3, 'D': 4})
data['grado_peligro_inundacion_CENAPRED'] = data['grado_peligro_inundacion_CENAPRED'].apply(grado_a_numero)
data['grado_vulnerabilidad_social_CENAPRED'] = data['grado_vulnerabilidad_social_CENAPRED'].apply(grado_a_numero)

# Cambiar la variable tiene_ARM de Sí y No a True y False
data['tiene_ARM'] = data['tiene_ARM'].map({'Sí': True, 'No': False})

#definción de los pesos de cada riesgo y falta de ARM.
PESO_SISMICA       = 0.30
PESO_INUNDACION    = 0.35
PESO_VULNERABILIDAD = 0.25
BONO_SIN_ARM       = 0.10

data['prioridad'] = (
    PESO_SISMICA * data['zona_sismica_CFE'] +
    PESO_INUNDACION * data['grado_peligro_inundacion_CENAPRED'] +
    PESO_VULNERABILIDAD * data['grado_vulnerabilidad_social_CENAPRED'] +
    data['tiene_ARM'].apply(lambda tiene: 0 if tiene else BONO_SIN_ARM)
)

idx_max = data['prioridad'].idxmax()
idx_min = data['prioridad'].idxmin()

print("Municipio mayor prioridad:", data.loc[idx_max, 'municipio'], f"({data.loc[idx_max, 'prioridad']:.4f})")
print("Municipio menor prioridad:", data.loc[idx_min, 'municipio'], f"({data.loc[idx_min, 'prioridad']:.4f})")

N_MUNICIPIOS = len(data)  # 267 en este caso, pero podría usarse otro dataset
TAM_POBLACION = 150       # número de cromosomas, se decidió 150

def inicializar_poblacion(tam_poblacion, n_municipios):
    poblacion = []
    for _ in range(tam_poblacion):
        genes = np.random.random(n_municipios)
        cromosoma = genes / genes.sum()  # normalizar para que sume 1
        poblacion.append(cromosoma)
    return poblacion

poblacion = inicializar_poblacion(TAM_POBLACION, N_MUNICIPIOS)

PRESUPUESTO_TOTAL = 10_000_000
prioridades = data['prioridad'].values  # arreglo de 267 prioridades
#Función fitness, se recompensa cuando se asigna más presupuesto a municipios con mayor prioridad
def fitness(cromosoma):
    presupuestos = cromosoma * PRESUPUESTO_TOTAL
    return np.sum(presupuestos * prioridades)

K_TORNEO = 5  # tamaño del torneo, algo pequeño para generar diversidad y compensar
              # el tamaño pequeño de la población inicial, aunque suficiente grande para no
              # dejar pasar individuos poco aptos

def seleccion_torneo(poblacion, fitnesses, k=K_TORNEO):
    indices = np.random.choice(len(poblacion), k, replace=False)
    mejor_indice = max(indices, key=lambda i: fitnesses[i])
    return poblacion[mejor_indice]

#Se usa cruzamiento uniforme, para promover diversidad
def cruzamiento(padre1, padre2):
    mascara = np.random.random(N_MUNICIPIOS) > 0.5
    hijo = np.where(mascara, padre1, padre2)
    hijo = hijo / hijo.sum()  # renormalizar
    return hijo

def mutacion(cromosoma, tasa):
    cromosoma = cromosoma.copy()  # no modificar el original
    if np.random.random() < tasa: # la mutación no ocurre siempre, solo con probabilidad tasa
        i, j = np.random.choice(N_MUNICIPIOS, 2, replace=False)
        delta = np.random.uniform(0, cromosoma[i]) #cantidad aleatoria a mover, máximo lo que tiene
        cromosoma[i] -= delta                      #el municipio i para no generar valores negativos
        cromosoma[j] += delta # transfiere presupuesto de uno al otro, la suma sigue siendo 1
    return cromosoma

#Ciclo principal
N_GENERACIONES = 800 #Se decidieron 400 generaciones para más posibilidades de una mejor solución.

def ciclo_ag(tasa_mutacion, n_generaciones=N_GENERACIONES):
    # Inicializar población
    poblacion = inicializar_poblacion(TAM_POBLACION, N_MUNICIPIOS)
    
    historial_fitness = []  # para la gráfica de convergencia

    for generacion in range(n_generaciones):
        # Evaluar fitness de toda la población
        fitnesses = [fitness(cromosoma) for cromosoma in poblacion]
        
        # Guardar el fitness promedio de esta generación
        historial_fitness.append(np.mean(fitnesses))
        
        # Generar nueva población
        nueva_poblacion = []
        while len(nueva_poblacion) < TAM_POBLACION:
            padre1 = seleccion_torneo(poblacion, fitnesses)
            padre2 = seleccion_torneo(poblacion, fitnesses)
            hijo = cruzamiento(padre1, padre2)
            hijo = mutacion(hijo, tasa=tasa_mutacion)
            nueva_poblacion.append(hijo)
        
        # Reemplazar población anterior
        poblacion = nueva_poblacion
    
    # Al terminar, regresar el mejor cromosoma y el historial
    fitnesses = [fitness(cromosoma) for cromosoma in poblacion]
    mejor_indice = np.argmax(fitnesses)
    return poblacion[mejor_indice], fitnesses[mejor_indice], historial_fitness


"""
EXPERIMENTACIÓN.
Una vez teniendo todo el algoritmo genetico se obtienen resultados con las diferentes tasas 
de mutación.
"""
N_CORRIDAS = 5

def ejecutar_experimento(tasa):
    """Corre N_CORRIDAS y devuelve lista de resultados, imprimiendo resumen por corrida."""
    print(f"  EXPERIMENTO — tasa de mutación: {tasa}")
    resultados = []
    for corrida in range(N_CORRIDAS):
        mejor, fit, historial = ciclo_ag(tasa_mutacion=tasa)
        presupuestos = mejor * PRESUPUESTO_TOTAL
 
        # Municipio que recibe más y menos presupuesto en esta corrida
        idx_max = np.argmax(presupuestos)
        idx_min = np.argmin(presupuestos)
 
        print(f"\n  Corrida {corrida + 1}/{N_CORRIDAS}")
        print(f"    Fitness           : {fit:,.2f}")
        print(f"    Presupuesto total : ${presupuestos.sum():,.2f}")
        print(f"    Mayor asignación  : {data['municipio'].iloc[idx_max]} "
              f"(${presupuestos[idx_max]:,.2f})")
        print(f"    Menor asignación  : {data['municipio'].iloc[idx_min]} "
              f"(${presupuestos[idx_min]:,.2f})")
 
        resultados.append({'cromosoma': mejor, 'fitness': fit, 'historial': historial})
 
    # Mejor de las 5 corridas
    mejor_corrida = max(resultados, key=lambda x: x['fitness'])
    print(f"\n  >> Mejor fitness de las {N_CORRIDAS} corridas: {mejor_corrida['fitness']:,.2f}")
    return resultados, mejor_corrida
 
resultados_001, mejor_001 = ejecutar_experimento(0.01)
resultados_008, mejor_008 = ejecutar_experimento(0.08)
 
 
# Exporta la mejor solución por tasa.
def exportar_csv(mejor_corrida, tasa, nombre_archivo):
    presupuestos = mejor_corrida['cromosoma'] * PRESUPUESTO_TOTAL
    df_resultado = data[['municipio', 'prioridad']].copy()
    df_resultado['presupuesto_asignado_MXN'] = presupuestos.round(2)
    df_resultado['porcentaje'] = (mejor_corrida['cromosoma'] * 100).round(4)
    df_resultado = df_resultado.sort_values('presupuesto_asignado_MXN', ascending=False)
    df_resultado.to_csv(nombre_archivo, index=False)
    print(f"\nArchivo guardado: {nombre_archivo}")
 
exportar_csv(mejor_001, 0.01, "mejor_solucion_tasa_001.csv")
exportar_csv(mejor_008, 0.08, "mejor_solucion_tasa_008.csv")

#Gráfica.
def graficar_convergencia(resultados, tasa, color):
    for r in resultados:
        plt.plot(r['historial'], color='gray', linewidth=1.2, alpha=0.45)
    historial_promedio = np.mean([r['historial'] for r in resultados], axis=0)
    plt.plot(historial_promedio, color=color, linewidth=2.5, label=f'Tasa {tasa}')
 
plt.figure(figsize=(10, 5))
 
graficar_convergencia(resultados_001, tasa=0.01, color='steelblue')
graficar_convergencia(resultados_008, tasa=0.08, color='crimson')
 
plt.xlabel('Generación')
plt.ylabel('Fitness promedio')
plt.title('Convergencia del AG — Comparativa de tasas de mutación')
plt.legend()
plt.tight_layout()
plt.savefig('convergencia.png', dpi=150)
plt.show()