# PROTOCOLO DE OPTIMIZACION DE CONTEXTO Y AHORRO DE TOKENS (GRAFT)

Este repositorio cuenta con un Grafo de Contexto generado por Graft en la carpeta `graft/`.
Para resolver cualquier tarea, DEBES seguir estas reglas estrictas para ahorrar tokens:

1. PROHIBIDO LEER ARCHIVOS COMPLETOS A CIEGAS:
   - No hagas lecturas masivas ni abras archivos enteros para buscar codigo.
   - Consulta primero el nodo en `graft/` o ejecuta `graft ask "<tarea>"` para obtener archivos y lineas exactos.

2. ESQUELETO DE CODIGO (SKELETON):
   - Si necesitas conocer firmas, metodos o tipos de un servicio, ejecuta:
     `graft skeleton <ruta_archivo>` (ahorra 90% de tokens frente al archivo completo).

3. ANALISIS DE IMPACTO:
   - Antes de modificar una funcion o componente compartido, ejecuta:
     `graft callers <nombre_simbolo>` para conocer todas las llamadas dependientes.

4. EDICIONES PRECISAS:
   - Lee y edita unicamente las lineas necesarias. Evita reescribir archivos enteros.
