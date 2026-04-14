# Buenas Prácticas de Push, Pull y Rebase en Cambios Grandes

> Guía práctica basada en un caso real del proyecto ECOMPARTS Marketplace.
> Fecha: 2 de abril de 2026

---

## 1. Objetivo

Cuando el trabajo local es grande y la rama remota ya cambió, hacer `push` deja de ser un paso trivial.

El riesgo no es solo tener conflictos de código. También pueden aparecer:

- conflictos de contenido entre cambios tuyos y cambios remotos,
- archivos sin commit que se mezclan con el `pull`,
- archivos no trackeados que bloquean el checkout de Git,
- permisos incorrectos en archivos generados por Docker u otros procesos,
- dependencias nuevas que obligan a reconstruir contenedores o reinstalar paquetes.

Esta guía resume un flujo seguro para publicar cambios grandes sin perder trabajo y sin resolver conflictos a ciegas.

---

## 2. Principio rector

### Nunca hagas `pull` sobre un árbol sucio si todavía no protegiste tu trabajo

Si tienes muchos cambios locales sin commit y haces `pull` de inmediato, Git puede mezclar:

- tu trabajo no confirmado,
- cambios del remoto,
- archivos parcialmente solapados,
- conflictos más difíciles de leer.

La práctica correcta es:

1. dejar tu trabajo protegido en un commit local,
2. traer el remoto,
3. integrar encima,
4. resolver conflictos con contexto y control.

---

## 3. Flujo recomendado para pushes grandes

### Paso 1. Revisar estado antes de tocar nada

```bash
git status -sb
git branch --show-current
git remote -v
```

Esto confirma:

- en qué rama estás,
- si tienes cambios locales,
- contra qué remoto vas a trabajar.

---

### Paso 2. Hacer commit local antes de integrar remoto

Si tu trabajo ya está listo para protegerse, haz primero el commit local.

```bash
git add -A
git commit
```

Si el cambio es grande, conviene usar un mensaje estructurado y detallado.

Ventaja:

- tu trabajo queda encapsulado,
- cualquier conflicto se verá contra commits, no contra archivos sin confirmar,
- puedes abortar integración sin perder cambios.

---

### Paso 3. Traer remoto sin modificar tu árbol

```bash
git fetch origin
```

`fetch` actualiza referencias remotas, pero no toca tu working tree.

Esto te permite inspeccionar la situación real antes de decidir cómo integrar.

---

### Paso 4. Integrar con `rebase` cuando quieres revisar conflictos tú mismo

```bash
git rebase origin/main
```

Esto toma tu commit local y lo reaplica encima de la punta remota.

Ventajas en proyectos con trabajo reciente de varias personas:

- deja la historia lineal,
- los conflictos quedan concentrados en tus commits,
- es más fácil entender qué parte vino del remoto y qué parte vino de tu trabajo.

### Cuándo preferir `merge`

Si el equipo prefiere preservar explícitamente el punto de unión entre historias, puede usarse:

```bash
git merge origin/main
```

Pero cuando el objetivo es revisar tus conflictos con precisión y luego publicar limpio, `rebase` suele ser más cómodo.

---

## 4. Qué hacer si aparecen conflictos

Durante el rebase, Git puede detenerse con un mensaje similar a este:

```bash
CONFLICTO (contenido): Conflicto de fusión en archivo
error: no se pudo aplicar <commit>
```

El flujo correcto es:

1. abrir solo los archivos en conflicto,
2. leer ambos lados con calma,
3. decidir manualmente qué conservar,
4. quitar marcadores `<<<<<<<`, `=======`, `>>>>>>>`,
5. marcar resolución con `git add archivo`,
6. continuar con:

```bash
git rebase --continue
```

### No hagas esto

- no aceptes todos los cambios “incoming” por reflejo,
- no aceptes todos los cambios “current” por reflejo,
- no resuelvas a ciegas archivos de infraestructura o sincronización,
- no sigas con el rebase si todavía quedan marcadores de conflicto.

---

## 5. Caso real visto en este proyecto

En este caso ocurrió el siguiente flujo:

1. Había un cambio local grande en `main`.
2. `origin/main` también tenía cambios nuevos de otro compañero.
3. Se hizo primero un commit local para proteger el trabajo.
4. Se ejecutó `git fetch origin`.
5. Se intentó `git rebase origin/main`.
6. El primer intento no falló por conflicto de código, sino por permisos de archivos dentro de Odoo.
7. Después de corregir el estado del árbol y permisos, el rebase sí avanzó.
8. Los conflictos reales aparecieron en:
   - `services/backend/apps/sync/odoo_connector.py`
   - `services/backend/apps/sync/tasks.py`
9. Se resolvieron manualmente.
10. Se completó el rebase con `git rebase --continue`.
11. Finalmente se hizo:

```bash
git push origin main
```

Resultado:

- trabajo local preservado,
- cambios remotos integrados,
- conflictos resueltos con criterio humano,
- historial publicado sin perder contexto.

---

## 6. Problemas típicos y cómo resolverlos

### Caso A. `push` rechazado porque el remoto avanzó

Síntoma:

```bash
! [rejected] main -> main (fetch first)
```

Solución:

```bash
git fetch origin
git rebase origin/main
git push origin main
```

---

### Caso B. Tienes cambios locales sin commit

Síntoma:

```bash
git status
```

y aparecen muchos archivos modificados.

Solución recomendada:

```bash
git add -A
git commit
git fetch origin
git rebase origin/main
```

Alternativa temporal si aún no quieres commit:

```bash
git stash push -u
git fetch origin
git rebase origin/main
git stash pop
```

Pero en cambios grandes y ya maduros, el commit local es más seguro que depender solo de stash.

---

### Caso C. Archivos no trackeados bloquean el rebase

Síntoma típico:

Git no puede hacer checkout porque un archivo no trackeado ocuparía la ruta de uno trackeado del remoto.

Primero inspecciona qué es:

```bash
git status -sb
```

Si son residuos temporales y no trabajo real:

```bash
git clean -fd -- ruta
```

Si sí son trabajo real, protégelos antes:

```bash
git stash push -u -m "temporal"
```

---

### Caso D. Permisos incorrectos en archivos generados por Docker

Síntoma:

```bash
error: unable to unlink old 'archivo': Permiso denegado
```

Esto suele pasar cuando un contenedor escribió archivos como otro usuario.

Revisar propietario:

```bash
ls -l archivo
```

Corregir propiedad:

```bash
sudo chown -R $USER:$USER ruta
```

Ejemplo real de este proyecto:

```bash
sudo chown -R $USER:$USER services/odoo/addons/ecomparts_integration
```

### Buena práctica preventiva

Si usas Docker con volúmenes montados, intenta que el contenedor escriba con tu mismo UID/GID o limita al máximo los directorios que el contenedor modifica en el árbol del repo.

---

### Caso E. El rebase quedó a medias y el working tree raro

Si el intento falló temprano y quieres volver al punto seguro anterior:

```bash
git rebase --abort
```

Si Git no considera que el rebase siga activo, pero el árbol quedó mezclado y sabes que tu commit local ya estaba protegido:

```bash
git reset --hard HEAD
```

### Advertencia

`git reset --hard HEAD` solo debe hacerse si ya sabes que tu trabajo está a salvo en un commit o stash.

---

### Caso F. Nueva dependencia después de integrar

Si cambió `requirements.txt`, `package.json`, Dockerfiles o variables de entorno, el push no es el final del proceso.

Debes actualizar entorno y validar arranque.

Ejemplos:

#### Backend Python

```bash
pip install -r services/backend/requirements.txt
```

#### Si usas Docker Compose

```bash
docker compose build backend
docker compose build worker
docker compose up -d backend worker
```

Si backend y worker comparten imagen, hay que reconstruir ambos caminos de ejecución aunque el cambio sea uno solo.

---

## 7. Flujo seguro resumido

```bash
git status -sb
git add -A
git commit
git fetch origin
git rebase origin/main

# si hay conflictos:
# editar archivos
git add <archivos>
git rebase --continue

git push origin main
```

Si hay dependencias nuevas o cambios de infraestructura:

```bash
# reconstruir / reinstalar
# validar arranque
```

---

## 8. Buenas prácticas concretas para equipos

### 1. Haz commits locales antes de integrar remoto

Proteges el trabajo y simplificas los conflictos.

### 2. Usa `fetch` antes de decidir

No mezcles traer información remota con modificar tu working tree.

### 3. Resuelve conflictos con criterio funcional, no solo textual

La pregunta correcta no es “qué bloque se ve más nuevo”, sino “qué comportamiento debe quedar”.

### 4. Infraestructura y sincronización merecen revisión más cuidadosa

Archivos como:

- conectores Odoo,
- tareas Celery,
- Docker Compose,
- settings,
- migraciones,

deben revisarse con especial atención porque una mezcla incorrecta puede romper despliegue, sincronización o datos.

### 5. No uses `push --force` en `main` salvo que el equipo lo haya acordado explícitamente

En ramas compartidas, un `push --force` puede borrar trabajo ajeno publicado.

### 6. Si el repo usa Docker, vigila ownership de archivos del árbol

Muchos problemas de Git “raros” son en realidad problemas de permisos.

### 7. Después del push, el trabajo no siempre terminó

Si cambiaste dependencias, migraciones o infraestructura, todavía falta:

- reconstruir entorno,
- correr migraciones si aplica,
- validar arranque,
- revisar logs si algo falla.

---

## 9. Checklist antes de hacer push en cambios grandes

- `git status -sb` limpio o entendido
- commit local creado
- `git fetch origin` ejecutado
- integración hecha con `rebase` o `merge`
- conflictos resueltos manualmente
- working tree limpio otra vez
- dependencias nuevas identificadas
- entorno reconstruido si aplica
- validación mínima ejecutada
- recién entonces `git push origin main`

---

## 10. Comandos útiles de referencia

```bash
# Ver estado resumido
git status -sb

# Ver rama actual
git branch --show-current

# Traer remoto sin tocar archivos locales
git fetch origin

# Reaplicar commits locales encima del remoto
git rebase origin/main

# Continuar rebase tras resolver conflictos
git add archivo
git rebase --continue

# Abortar rebase
git rebase --abort

# Limpiar archivos no trackeados en una ruta específica
git clean -fd -- ruta

# Guardar trabajo temporal incluyendo no trackeados
git stash push -u -m "mensaje"

# Ver stashes
git stash list

# Corregir ownership de archivos escritos por Docker
sudo chown -R $USER:$USER ruta
```

---

## 11. Conclusión

Hacer `push` en proyectos grandes no es difícil porque Git sea caprichoso. Es difícil porque ya no solo estás publicando archivos: estás integrando historia, infraestructura, permisos, dependencias y decisiones de otras personas.

La idea correcta no es “hacer push rápido”. La idea correcta es “hacer push sin perder control”.

En este proyecto, el flujo seguro fue:

- commit local,
- fetch,
- rebase,
- corrección de permisos,
- resolución manual de conflictos,
- continue,
- push.

Ese es el patrón que conviene repetir cuando el cambio es grande y la rama remota ya avanzó.
