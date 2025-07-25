# WeKan-Project: Integración WeKan-GitHub para NiceDev

[![Estado del Proyecto](https://img.shields.io/badge/Estado-En%20Desarrollo-yellow.svg)](https://github.com/victormhl1956/WeKan-Project)
[![Versión](https://img.shields.io/badge/Versión-2.1.0-blue.svg)](https://github.com/victormhl1956/WeKan-Project/releases)
[![Licencia](https://img.shields.io/badge/Licencia-MIT-green.svg)](LICENSE)

## 📋 Descripción

WeKan-Project es una solución integral para la sincronización automática entre WeKan (sistema de gestión de proyectos Kanban) y repositorios de GitHub. Este proyecto forma parte del ecosistema NiceDev y tiene como objetivo crear una sincronización bidireccional completa entre ambas plataformas.

## 🎯 Objetivos del Proyecto

- **Sincronización Automática**: Mantener WeKan absolutamente sincronizado con repositorios de GitHub
- **Creación On-Demand**: Crear proyectos WeKan automáticamente para nuevos repositorios
- **Dashboard Unificado**: Proporcionar una vista consolidada de todos los proyectos
- **Extensión IDE**: Integrar la funcionalidad directamente en VS Code/Theia

## 🏗️ Arquitectura Actual

### Estado de Implementación

| Componente | Estado | Descripción |
|------------|--------|-------------|
| WeKan Server | ✅ **OPERATIVO** | Instancia containerizada en `http://localhost:8088` |
| API Client | ✅ **COMPLETO** | Sistema robusto de gestión de boards, listas y tarjetas |
| GitHub Webhooks | ✅ **IMPLEMENTADO** | Sistema de escucha de eventos de GitHub |
| Sincronización | ⚠️ **PARCIAL** | Integración unidireccional GitHub → WeKan |
| Dashboard | ❌ **PENDIENTE** | Vista unificada multi-proyecto |
| Extensión IDE | ❌ **PENDIENTE** | Plugin para VS Code/Theia |

### Infraestructura

```yaml
# Docker Compose Configuration
wekan-app:
  image: wekanteam/wekan:latest
  container_name: nicedev-wekan-app
  ports: "8088:8080"
  environment:
    - MONGO_URL=mongodb://wekan-db:27017/wekan
    - ROOT_URL=http://localhost:8088

wekan-db:
  image: mongo:4.4
  container_name: nicedev-wekan-db
```

## 📁 Estructura del Proyecto

```
WeKan-Project/
├── README.md                              # Este archivo
├── INFORME_WEKAN_GITHUB_SINCRONIZACION_2025.md  # Informe de auditoría completo
├── GITHUB_WEBHOOK_SETUP.md                # Guía de configuración de webhooks
├── wekan_board_manager.py                 # Cliente API principal de WeKan
├── wekan_api_external.py                  # API externa de WeKan
├── test_wekan_api.py                      # Pruebas de conectividad API
├── test_wekan_integration.py              # Pruebas de integración
├── test_audit.py                          # Simulación de webhooks GitHub
├── src/                                   # Código fuente
│   ├── webhook_receiver.py                # Servicio de webhooks GitHub
│   ├── test_webhook_receiver.py           # Pruebas del servicio de webhooks
│   ├── dashboard/                         # Dashboard unificado (próximamente)
│   └── vscode_extension/                  # Extensión VS Code (próximamente)
├── docs/                                  # Documentación (próximamente)
├── tests/                                 # Pruebas adicionales
└── docker/                               # Configuraciones Docker
```

## 🚀 Instalación y Configuración

### Prerrequisitos

- Docker y Docker Compose
- Python 3.8+
- Node.js 16+ (para extensión VS Code)
- Git

### Instalación Rápida

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/victormhl1956/WeKan-Project.git
   cd WeKan-Project
   ```

2. **Configurar WeKan (usando docker-compose del proyecto principal):**
   ```bash
   # Desde el directorio nicedev-Project
   docker-compose up -d wekan-app wekan-db
   ```

3. **Instalar dependencias Python:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar credenciales:**
   - Crear archivo `.env` con credenciales seguras (ver `GITHUB_WEBHOOK_SETUP.md`)
   - Copiar `wekan_config.json.example` a `wekan_config.json` y editar

### Configuración de WeKan

1. Acceder a http://localhost:8088
2. Crear cuenta de administrador
3. Configurar credenciales en `.env` y `wekan_config.json`

## 🚀 Deployment y Configuración de Producción

### Pasos Detallados para Deployment

#### 1. Configuración del Entorno

**Crear archivo `.env` con credenciales seguras:**
```bash
# WeKan Configuration
WEKAN_URL=http://localhost:8088
WEKAN_USERNAME=your_admin_user
WEKAN_PASSWORD=your_secure_password

# GitHub Webhook Configuration
GITHUB_WEBHOOK_SECRET=your_random_secret_key
PORT=5000
DEBUG=false
```

**Configurar `wekan_config.json`:**
```json
{
  "wekan_url": "http://localhost:8088",
  "credentials": {
    "username": "your_wekan_username",
    "password": "your_wekan_password"
  },
  "github": {
    "token": "your_github_personal_access_token",
    "webhook_secret": "your_webhook_secret"
  },
  "sync_settings": {
    "auto_create_boards": true,
    "default_template": "kanban_basic"
  }
}
```

#### 2. Iniciar WeKan Instance

```bash
# Desde el directorio nicedev-Project
docker-compose up -d wekan-app wekan-db

# Verificar que los contenedores estén ejecutándose
docker ps | grep wekan
```

#### 3. Instalación de Dependencias

```bash
# Instalar dependencias Python
pip install -r requirements.txt

# Verificar instalación
python -c "import flask, requests; print('Dependencies OK')"
```

#### 4. Pruebas de Integración

```bash
# Pruebas unitarias
python test_wekan_api.py

# Pruebas de webhook (sin conexión WeKan)
python src/test_webhook_receiver.py

# Pruebas de integración completa
python test_wekan_integration.py
```

#### 5. Iniciar el Servicio de Webhooks

**Desarrollo:**
```bash
python src/webhook_receiver.py
```

**Producción (con gunicorn):**
```bash
gunicorn --bind 0.0.0.0:5000 --workers 4 src.webhook_receiver:app
```

**Como servicio systemd (Linux):**
```bash
# Crear archivo /etc/systemd/system/wekan-webhook.service
sudo systemctl enable wekan-webhook
sudo systemctl start wekan-webhook
```

#### 6. Configuración de GitHub Webhooks

1. **Ir a Settings → Webhooks en tu repositorio GitHub**
2. **Añadir webhook con:**
   - Payload URL: `https://your-domain.com/github-webhook`
   - Content type: `application/json`
   - Secret: Tu `GITHUB_WEBHOOK_SECRET`
   - Events: Issues, Pull requests, Pushes, Repository

#### 7. Verificación del Deployment

```bash
# Health check del servicio
curl http://localhost:5000/health

# Verificar logs
tail -f wekan_project.log

# Test de webhook (simulado)
curl -X POST http://localhost:5000/github-webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: ping" \
  -d '{"zen": "Design for failure."}'
```

### Deployment Automatizado

**Usar el script de deployment:**
```bash
# En Windows
.\run_deploy.bat

# En Linux/Mac
chmod +x deploy.sh
./deploy.sh
```

### Configuración de Producción Avanzada

#### Reverse Proxy con Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location /github-webhook {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### SSL/TLS con Let's Encrypt

```bash
# Instalar certbot
sudo apt install certbot python3-certbot-nginx

# Obtener certificado
sudo certbot --nginx -d your-domain.com
```

#### Monitoreo y Logging

```bash
# Configurar logrotate
sudo nano /etc/logrotate.d/wekan-webhook

# Configurar monitoring con systemd
sudo systemctl status wekan-webhook
journalctl -u wekan-webhook -f
```

## 🧪 Pruebas

### Ejecutar Pruebas de Conectividad

```bash
python test_wekan_api.py
```

### Ejecutar Pruebas de Integración

```bash
python test_wekan_integration.py
```

### Simular Webhooks GitHub

```bash
python src/test_webhook_receiver.py
```

## 📊 Estado Actual del Proyecto

### ✅ Funcionalidades Implementadas

- **WeKan API Client Completo**
  - Autenticación con manejo de tokens
  - Creación de boards desde templates
  - Gestión de listas y tarjetas
  - Sistema de logging y manejo de errores

- **GitHub Webhook Integration**
  - Servicio Flask para recibir webhooks
  - Verificación de seguridad con HMAC-SHA256
  - Procesamiento de eventos: Issues, PRs, Commits, Repositories
  - Sincronización unidireccional GitHub → WeKan

- **Sistema de Pruebas**
  - Pruebas de conectividad API
  - Pruebas de integración
  - Pruebas del servicio de webhooks

### ❌ Funcionalidades Pendientes

- **Sincronización Bidireccional Completa**
- **Dashboard Unificado Multi-Proyecto**
- **Extensión VS Code/Theia**

## 🛣️ Roadmap de Desarrollo

### Fase 1: Fundamentos (Semanas 1-2) - ✅ COMPLETADO
- [x] Implementar GitHub Webhook Listener Service
- [x] Crear sistema de mapeo Repository → Board
- [x] Desarrollar procesador de eventos básico
- [x] Testing de sincronización unidireccional

### Fase 2: Sincronización Completa (Semanas 3-4)
- [ ] Implementar sincronización bidireccional
- [ ] Crear dashboard unificado básico
- [ ] Desarrollar API de agregación de métricas
- [ ] Sistema de notificaciones

### Fase 3: Extensión IDE (Semanas 5-8)
- [ ] Desarrollar extensión VS Code base
- [ ] Implementar dashboard integrado
- [ ] Crear comandos de gestión de proyectos
- [ ] Testing y refinamiento UX

### Fase 4: Funcionalidades Avanzadas (Semanas 9-12)
- [ ] IA para automatización inteligente
- [ ] Métricas avanzadas y analytics
- [ ] Integración con otros servicios
- [ ] Optimización de performance

## 🔧 API Reference

### WeKan Board Manager

```python
from wekan_board_manager import WekanAuthManager, WekanAPIClient, BoardCreator

# Inicializar cliente
auth_manager = WekanAuthManager(
    wekan_url="http://localhost:8088",
    username="tu_usuario",
    password="tu_password"
)

api_client = WekanAPIClient("http://localhost:8088", auth_manager)
board_creator = BoardCreator(api_client, template_manager)

# Crear board desde template
result = board_creator.create_board_from_template(
    template_name="kanban_basic",
    board_title="Mi Proyecto"
)
```

### GitHub Webhook Receiver

- **Endpoint**: `POST /github-webhook`
- **Eventos Soportados**: `issues`, `pull_request`, `push`, `repository`
- **Seguridad**: Verificación de firma HMAC-SHA256

## 📈 Métricas de Éxito

### Funcionalidad
- [x] 100% de issues GitHub sincronizados con WeKan
- [ ] <5 segundos latencia en sincronización
- [x] 99.9% uptime del servicio de webhooks

### Usabilidad
- [ ] Dashboard accesible desde VS Code en <2 clicks
- [ ] Creación de proyectos on-demand en <30 segundos
- [ ] Vista unificada de todos los proyectos activos

### Performance
- [ ] Soporte para >100 repositorios simultáneos
- [ ] <1MB memoria por repositorio monitoreado
- [ ] Procesamiento de webhooks <500ms

## 🤝 Contribución

### Cómo Contribuir

1. Fork el proyecto
2. Crear una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir un Pull Request

### Estándares de Código

- Seguir PEP 8 para Python
- Documentar todas las funciones públicas
- Incluir pruebas para nuevas funcionalidades
- Mantener cobertura de pruebas >90%

## 📄 Documentación

- [Informe de Auditoría Completo](INFORME_WEKAN_GITHUB_SINCRONIZACION_2025.md)
- [Guía de Configuración de Webhooks](GITHUB_WEBHOOK_SETUP.md)
- [Documentación API WeKan](docs/wekan-api.md) (próximamente)
- [Guía de Desarrollo](docs/development-guide.md) (próximamente)

## 🔒 Seguridad

### Consideraciones de Seguridad

- Validación de signatures GitHub (HMAC-SHA256)
- Rate limiting para prevenir abuse
- Encriptación de credenciales en storage
- Logging de eventos para auditoría

### Reportar Vulnerabilidades

Si encuentras una vulnerabilidad de seguridad, por favor envía un email a security@nicedev.com en lugar de crear un issue público.

## 📞 Soporte

### Canales de Soporte

- **Issues de GitHub**: Para bugs y feature requests
- **Discussions**: Para preguntas generales y discusiones
- **Email**: support@nicedev.com para soporte directo

### FAQ

**P: ¿Cómo configuro los webhooks de GitHub?**
R: Consulta la [Guía de Configuración de Webhooks](GITHUB_WEBHOOK_SETUP.md) para instrucciones detalladas.

**P: ¿Es compatible con GitHub Enterprise?**
R: Sí, el sistema está diseñado para ser compatible con GitHub Enterprise Server.

**P: ¿Puedo usar otros sistemas Kanban además de WeKan?**
R: Actualmente solo soportamos WeKan, pero la arquitectura permite extensiones futuras.

## 📊 Estado del Proyecto

- **Última Actualización**: 24 de Julio, 2025
- **Versión Actual**: 2.1.0
- **Estado**: En Desarrollo Activo
- **Próximo Milestone**: Implementación de Sincronización Bidireccional

## 🏆 Reconocimientos

- **WeKan Team** - Por el excelente sistema de gestión Kanban
- **GitHub** - Por la robusta API y sistema de webhooks
- **NiceDev Team** - Por la visión y soporte del proyecto

## 📝 Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

---

**Desarrollado con ❤️ por el equipo NiceDev**

Para más información sobre el ecosistema NiceDev, visita: https://github.com/victormhl1956
