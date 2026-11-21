# Glosario para no expertos

| Término | Significado simple |
|---|---|
| **Contenedor** | Una "cajita" con la aplicación y lo que necesita, que corre igual en cualquier computador. |
| **Imagen / Dockerfile** | La "receta" (Dockerfile) y el resultado empaquetado (imagen) a partir del cual se crean contenedores. |
| **Docker Compose / `compose.yaml`** | Archivo que describe todas las cajitas y cómo se conectan; se levanta con un comando. |
| **Instancia** | Una copia en ejecución del servicio (`app1`, `app2`). Con dos, una puede fallar sin parar todo. |
| **Proxy inverso (NGINX)** | El "portero": único punto de entrada; reparte consultas y reintenta con otra instancia si una no responde. |
| **Upstream** | Cada instancia detrás del proxy. En los registros indica quién atendió la consulta. |
| **Detección pasiva** | El proxy se entera de que una instancia falló *cuando intenta usarla*. No hace chequeos por su cuenta. |
| **Healthcheck / `/health`** | Pregunta "¿estás bien?". Docker la usa para marcar *healthy/unhealthy* y coordinar el arranque; por sí sola no reinicia ni retira nada. |
| **Almacenamiento efímero** | El espacio dentro del contenedor: se pierde al recrearlo. |
| **Montaje (bind mount)** | Conectar un archivo del computador al contenedor. Así `data/pedidos.json` queda **fuera** del contenedor y sobrevive. |
| **Persistir vs. respaldar** | Persistir = que el dato sobreviva a recrear el contenedor. Respaldar = tener una copia aparte por si el dato se daña o se pierde. Son cosas distintas. |
| **Hash (SHA-256)** | Huella digital de un archivo: si cambia un carácter, la huella cambia. Prueba que lo restaurado es idéntico. |
| **RTO** | Tiempo de recuperación: cuánto tarda el servicio en volver a estar bien. |
| **Punto único de fallo** | Pieza cuya caída detiene todo (aquí: el computador, el proxy y el archivo de datos compartido). |
| **Alta disponibilidad** | Diseño que tolera fallos incluso de una máquina o zona completa. Dos contenedores en un PC **no** lo son. |
| **Registros (logs)** | El "diario" de cada pieza; sirve para investigar incidentes. |
| **CI** | Robot (GitHub Actions) que valida y prueba el proyecto en cada cambio. |
| **Secreto** | Contraseña, clave o token. Nunca va en la imagen ni en el repositorio. |
