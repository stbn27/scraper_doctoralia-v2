# Documentación — Chatbot e Interpretación Médica

## POST `/chat/interpretar` _(Público)_

Convierte lenguaje natural del usuario en filtros de búsqueda para `GET /especialistas`.

**No diagnostica. No da tratamientos. No reemplaza a un médico.**

### Request Body

```json
{
  "consulta": "Tengo dolor de muela y soy de Ciudad de México",
  "messages": [
    { "role": "user", "content": "..." },
    { "role": "assistant", "content": "..." }
  ],
  "filtros_actuales": null,
  "provider": "groq",
  "auto_search": false
}
```

| Campo | Descripción |
|-------|-------------|
| `consulta` | Último mensaje del usuario |
| `messages` | Historial de la conversación (últimos 6 se usan) |
| `provider` | `groq` \| `gemini` \| `auto` |

`provider: auto` usa Groq por defecto con Gemini como fallback.

### Respuesta — Caso incompleto (`ready: false`)

```json
{
  "reply": "¿En qué ciudad te gustaría buscar?",
  "ready": false,
  "should_search": false,
  "detected": {
    "especialidad": "Endodoncia", "especialidad_slug": "endodoncia",
    "ciudad": null, "ciudad_slug": null,
    "atiende_adultos": true, "solo_analizados": true, "solo_con_opiniones": true
  },
  "missing_fields": ["ciudad"],
  "suggestions": [
    { "type": "city", "label": "Ciudad de México", "value": "ciudad-de-mexico" }
  ],
  "search_params": null,
  "safety": { "is_emergency": false, "message": null },
  "model": { "provider": "groq", "name": "llama-3.3-70b-versatile" }
}
```

### Respuesta — Caso completo (`ready: true`)

```json
{
  "reply": "Perfecto, encontré filtros suficientes...",
  "ready": true,
  "should_search": true,
  "search_params": {
    "especialidad": "endodoncia", "ciudad": "ciudad-de-mexico",
    "orden": "puntuacion_desc", "solo_analizados": true
  },
  "missing_fields": []
}
```

### Respuesta — Emergencia médica

```json
{
  "reply": "Lo que describes puede requerir atención inmediata...",
  "ready": false,
  "should_search": false,
  "safety": { "is_emergency": true, "message": "Recomendar atención urgente." }
}
```

### Señales de emergencia detectadas
- Dolor de pecho intenso
- Dificultad para respirar
- Pérdida de conciencia
- Sangrado abundante
- Idea suicida
- Violencia física / abuso sexual
- Embarazo con sangrado intenso
- Síntomas neurológicos graves

---

## POST `/chat/interpretar/auth` _(Autenticado)_

Igual que `/chat/interpretar` pero usa la **ciudad registrada del usuario** como contexto adicional para el LLM.

```
Authorization: Bearer <token>
```

---

## POST `/recomendar`

Interpreta la consulta y ejecuta la búsqueda si tiene datos suficientes.

### Request

```json
{
  "consulta": "Tengo dolor fuerte de muela y soy de CDMX",
  "provider": "auto",
  "limit": 6
}
```

### Respuesta — Con datos suficientes

```json
{
  "interpretacion": {
    "ready": true,
    "especialidad": "Endodoncia",
    "ciudad": "Ciudad de México",
    "search_params": { "especialidad": "endodoncia", "ciudad": "ciudad-de-mexico" }
  },
  "results": [ { ...card de especialista... } ]
}
```

### Respuesta — Sin datos suficientes

```json
{
  "interpretacion": {
    "ready": false,
    "missing_fields": ["ciudad"],
    "reply": "¿En qué ciudad te gustaría buscar?"
  },
  "results": []
}
```

---

## Especialidades que detecta el LLM

| Síntoma / Descripción | Especialidad | Slug |
|----------------------|--------------|------|
| Dolor de muela, caries | Dentista / Endodoncia | `dentista` / `endodoncia` |
| Ansiedad, depresión, estrés | Psicólogo | `psicologo` |
| Problemas de pareja | Psicólogo | `psicologo` |
| Embarazo, menstruación | Ginecólogo | `ginecologo` |
| Corazón, presión alta | Cardiólogo | `cardiologo` |
| Piel, acné, manchas | Dermatólogo | `dermatologo` |
| Huesos, articulaciones | Ortopedista | `ortopedista` |
| Niños | Pediatra | `pediatra` |
| Ojos, visión | Oftalmólogo | `oftalmologo` |
| Oídos, nariz, garganta | Otorrinolaringólogo | `otorrinolaringologo` |

---

## Reglas de seguridad

1. ❌ No diagnostica enfermedades
2. ❌ No indica medicamentos ni dosis
3. ❌ No da tratamientos médicos
4. ✅ Detecta emergencias y recomienda urgencias
5. ✅ Sugiere especialidades basándose en síntomas
6. ✅ Pregunta cuando falta información
