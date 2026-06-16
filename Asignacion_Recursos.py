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
def conversion(grado):
     return {'Muy bajo': 1, 'Bajo': 2, 'Medio': 3, 'Alto': 4, 'Muy alto': 5}[grado]

data['zona_sismica_CFE'] = data['zona_sismica_CFE'].map({'A': 1, 'B': 2, 'C': 3, 'D': 4})
data['grado_peligro_inundacion_CENAPRED'] = data['grado_peligro_inundacion_CENAPRED'].apply(conversion)
data['grado_vulnerabilidad_social_CENAPRED'] = data['grado_vulnerabilidad_social_CENAPRED'].apply(conversion)

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

N_MUNICIPIOS = len(data)  # 267 en este caso
TAM_POBLACION = 150       # número de cromosomas, se decidió 150
PRESUPUESTO_TOTAL = 10_000_000
N_GENERACIONES = 800 #Se decidieron 800 generaciones para más posibilidades de una mejor solución.
K_TORNEO = 5  # tamaño del torneo, algo pequeño para generar diversidad y compensar
              # el tamaño pequeño de la población inicial, aunque suficiente grande para no
              # dejar pasar individuos poco aptos

#Para hacer un cambio de arquitectura, decidí crear una clase llamada AG, para ingresar
#Todas las funciones dentro de ella y que cambie  respecto a la anterior arquitectura.
class AG:
    def __init__(self, prioridades, presupuesto, n_municipios, tam_poblacion,
                 n_generaciones, k_torneo, tasa_mutacion):
        self.prioridades = prioridades
        self.presupuesto = presupuesto
        self.n_municipios = n_municipios
        self.tam_poblacion = tam_poblacion
        self.n_generaciones = n_generaciones
        self.k_torneo = k_torneo
        self.tasa_mutacion = tasa_mutacion
        self.historial_fitness = []
        self.mejor_cromosoma = None
        self.mejor_fitness = None
    
    def poblacion(self):
        poblacion = []
        promedio_por_municipio = self.presupuesto / self.n_municipios
        for _ in range(self.tam_poblacion):
            cromosoma = np.random.uniform(0, promedio_por_municipio * 2, self.n_municipios)
            poblacion.append(cromosoma)      #Ahora no se normaliza desde el principio
        return poblacion
    
    def fitness(self, cromosoma):
        total = cromosoma.sum() #Suma los valores del cromosoma
        if total > self.presupuesto:   
            exceso = total - self.presupuesto #Calcula la diferencia entre presupuesto - suma de los genes en el cromosa
            penalizacion = (exceso * max(self.prioridades))*2 #El 2 es arbitario, ya que sin él el exceso en el presupuesto era muy grande
            return np.sum(cromosoma * self.prioridades) - penalizacion #Ahora penalizo por exceder el presupuesto
        limite = self.presupuesto * 0.03
        penalizacion_concentracion = np.sum(np.maximum(0, cromosoma - limite) * max(self.prioridades))
        return np.sum(cromosoma * self.prioridades) - penalizacion_concentracion          #exceder el presupuesto                 

    def torneo(self, poblacion, fitnesses):
        indices = np.random.choice(len(poblacion), self.k_torneo, replace=False)
        mejor_indice = max(indices, key=lambda i: fitnesses[i])
        return poblacion[mejor_indice]
    
    #Se usa cruzamiento uniforme, para promover diversidad
    def cruzamiento(self, padre1, padre2):
        mascara = np.random.random(self.n_municipios) > 0.5 #Es la misma lógica de la versión
        hijo = np.where(mascara, padre1, padre2)            #anterior
        return hijo

    def mutacion(self, cromosoma):
        cromosoma = cromosoma.copy()  # no modificar el original
        for i in range(self.n_municipios): #Vamos gen por gen
            if np.random.random() < self.tasa_mutacion: #si el random es menor a la tasa entonces hay mutación
                delta = np.random.uniform(-cromosoma[i], cromosoma[i] * 0.5) #Aseguramos que el gen no sea menor a 0
                cromosoma[i] = max(0, cromosoma[i] + delta)
        return cromosoma

    def evolucion(self):
        poblacion = self.poblacion()
        self.historial_fitness = []
 
        for _ in range(self.n_generaciones):
            fitnesses = [self.fitness(c) for c in poblacion]
            self.historial_fitness.append(np.mean(fitnesses))
 
            nueva_poblacion = []
            while len(nueva_poblacion) < self.tam_poblacion:
                padre1 = self.torneo(poblacion, fitnesses)
                padre2 = self.torneo(poblacion, fitnesses)
                hijo = self.cruzamiento(padre1, padre2)
                hijo = self.mutacion(hijo)
                nueva_poblacion.append(hijo)
            poblacion = nueva_poblacion
 
        fitnesses = [self.fitness(c) for c in poblacion]
        mejor_indice = np.argmax(fitnesses)
        self.mejor_cromosoma = poblacion[mejor_indice]
        self.mejor_fitness = fitnesses[mejor_indice]
        return self.mejor_cromosoma, self.mejor_fitness, self.historial_fitness


"""
EXPERIMENTACIÓN.
Una vez teniendo todo el algoritmo genetico se obtienen resultados con las diferentes tasas 
de mutación.
"""
N_CORRIDAS = 5

def ejecutar_experimento(tasa):
    #Instancia el AG con la tasa asginada, corre N_CORRIDAS y devuelve resultados con resumen por corrida
    print(f"  EXPERIMENTO — tasa de mutación: {tasa}")
    resultados = []
    for corrida in range(N_CORRIDAS):
        ag = AG(
            prioridades=data['prioridad'].values,
            presupuesto=PRESUPUESTO_TOTAL,
            n_municipios=N_MUNICIPIOS,
            tam_poblacion=TAM_POBLACION,
            n_generaciones=N_GENERACIONES,
            k_torneo=K_TORNEO,
            tasa_mutacion=tasa
        )
        mejor, fit, historial = ag.evolucion()
        presupuestos = mejor
 
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
def exportar_csv(mejor_corrida, nombre_archivo):
    presupuestos = mejor_corrida['cromosoma']
    df_resultado = data[['municipio', 'prioridad']].copy()
    df_resultado['presupuesto_asignado_MXN'] = presupuestos.round(2)
    df_resultado['porcentaje'] = (presupuestos / PRESUPUESTO_TOTAL * 100).round(4)
    df_resultado = df_resultado.sort_values('presupuesto_asignado_MXN', ascending=False)
    df_resultado.to_csv(nombre_archivo, index=False)
    print(f"\nArchivo guardado: {nombre_archivo}")
 
exportar_csv(mejor_001, "mejor_solucion_tasa_001.csv")
exportar_csv(mejor_008,  "mejor_solucion_tasa_008.csv")
 
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

"""
Cambios realizados en el programa:
Ahora el cromosoma no se normaliza, los genes son libres de tomar los valores posibles
dentro de los límites establecidos en la función fitness y mutación, o sea, de la segunda
generación en delante (que es donde afecta la mutación), las restricciones de la función mutación
afectan a los valores posbiles tomados. 
De igual forma la lógica de mutación cambió, ahora cada gen es "libre" de sumar o restar
cualquier valor dentro de las restricciones antes mencionada (No puede retarse un delta mayor al
valor del gen, y no se puede sumar un valor delta mayor a 1/2 del valor del gen).
Se agregó una penalización por pasarse del presupuesto. En la versión anterior no era necesario
pero en esta sí. También se agrega una penalización por concentrar muchos recursos en un solo municipio.
Cambié la arquitecura general. Ahora las funciones están dentro de una clase llamada AG.
No encontré otra forma de graficar más que guardar los valores cuando se corre el experimetno y
graficar por separado.
"""