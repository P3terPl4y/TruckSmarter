# SSH y publicación en GitHub

Se creó el 11/10/2026 una clave Ed25519 dedicada a TruckSmarter. Las claves de otros proyectos no se modificaron.

| Dato | Valor |
| --- | --- |
| Privada, solo en esta máquina | `/home/peter/.ssh/trucksmarter_github_ed25519` |
| Pública | `/home/peter/.ssh/trucksmarter_github_ed25519.pub` |
| Permisos | Privada 600, pública 644, directorio .ssh 700 |
| Fingerprint público | `SHA256:L75b4kLR4XJY6ithoBz8nlCazdERUUqJfBbQzs/LqH4` |

Clave pública para registrar en GitHub:

```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJgJUmfnaNLDK+RPRQI8nKkdu0/OdpMRXqPykY9yhy54 trucksmarter-github
```

Solo esta línea pública puede compartirse. La privada no se copia, imprime ni versiona. Esta clave se generó sin passphrase para el flujo de acceso automatizado; su protección depende de los permisos y del acceso a la máquina. Para sustituirla o añadir passphrase, coordinar el uso con el propietario y retirar la pública anterior de GitHub cuando termine la transición.

Se puede registrar como deploy key exclusiva del repositorio con escritura habilitada si se desea hacer push, o como clave SSH de la cuenta según la política del propietario. No basta acceso de lectura para publicar.

## Acceso explícito con esta identidad

```bash
GIT_SSH_COMMAND='ssh -F /dev/null -i /home/peter/.ssh/trucksmarter_github_ed25519 -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes' \
  git ls-remote git@github.com:P3terPl4y/TruckSmarter.git HEAD refs/heads/main
```

La verificación estricta requiere que GitHub ya tenga una clave de host confiable en known_hosts. No desactivar la comprobación ni confiar automáticamente en una huella de host obtenida por una conexión no verificada.

El propietario autorizó publicar al indicar que el repositorio ya estaba configurado. Antes de push: revisar archivos, confirmar pruebas y comprobar que la rama remota no contiene cambios ajenos. Usar un push normal; no force push. La clave privada permanece fuera del repositorio aunque los documentos mencionen su ruta.

El comando SSH puede pasarse por `GIT_SSH_COMMAND` solo durante una operación; no es necesario cambiar la configuración global SSH ni afectar otros proyectos. Si GitHub devuelve Permission denied (publickey), registrar la pública exacta mostrada arriba y confirmar permisos de escritura; no reutilizar silenciosamente otra identidad.

## Estado de esta preparación

El acceso SSH con esta identidad se comprobó correctamente contra `P3terPl4y/TruckSmarter`. La rama remota main seguía en `77a0155410a416ec2a7381be4c253c156dbbe3f3` al preparar la publicación. La configuración SSH se limita a este repositorio mediante `core.sshCommand`; origin utiliza la URL SSH. `-F /dev/null` evita cargar una configuración SSH del sistema con permisos incompatibles en este entorno, manteniendo la verificación estricta de la clave de host.
