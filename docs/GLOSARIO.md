# Glosario para no expertos

| Término | Significado simple |
|---|---|
| **Contenedor** | Una "cajita" que trae la aplicación y todo lo que necesita para correr igual en cualquier computador. |
| **Imagen** | La "receta congelada" a partir de la cual se crean contenedores (se define en el `Dockerfile`). |
| **Docker Compose** | Un archivo (`docker-compose.yml`) que describe todas las cajitas y cómo se conectan; se levanta con un comando. |
| **Instancia / réplica** | Una copia en ejecución del servicio. Tener 2 permite que una falle sin parar todo. |
| **Balanceador / proxy inverso** | El "portero": recibe todas las consultas y las reparte entre instancias sanas. Aquí: HAProxy. |
| **Punto de acceso común** | La única dirección que usa la gente (`http://localhost:8080`), sin saber cuántas instancias hay detrás. |
| **Health check (comprobación de salud)** | Pregunta automática "¿estás bien?" (`/health`). Si una instancia no responde, se deja de usar. |
| **Conmutación (failover)** | Pasar el trabajo de la instancia caída a la que sigue viva. |
| **Almacenamiento efímero** | El espacio *dentro* del contenedor: se pierde al recrearlo. Por eso los datos no se guardan ahí. |
| **Volumen** | Almacenamiento *fuera* del contenedor que sobrevive a su recreación. |
| **Respaldo (backup)** | Copia de seguridad guardada en otro lugar, con una "huella" (hash) para comprobar que no se dañó. |
| **Restauración** | Devolver los datos desde un respaldo. |
| **Hash (SHA-256)** | Huella digital de un archivo: si cambia una coma, la huella cambia. Sirve para probar que lo recuperado es idéntico. |
| **RTO** (tiempo de recuperación) | Cuánto tarda el servicio en volver a estar bien tras un fallo. |
| **RPO** (punto de recuperación) | Cuánta información reciente se podría perder (depende de cada cuánto se hace el respaldo). |
| **Alta disponibilidad (HA)** | Diseño que tolera fallos de componentes *incluyendo* una máquina o zona completa. Dos contenedores en un PC **no** lo es. |
| **Registros (logs)** | El "diario" de lo que hace cada pieza; sirve para investigar incidentes. |
| **Escalar** | Aumentar instancias (o recursos) cuando crece la demanda. |
| **CI (integración continua)** | Robot (GitHub Actions) que valida y prueba el proyecto en cada cambio. |
| **Secreto** | Contraseña, clave o token. Nunca va dentro de la imagen ni del repositorio. |
