-- ============================================================================
-- CONFIGURACIÓN DE SUPABASE PARA HISTORIAL DE CONVERSACIONES
-- ============================================================================
-- Ejecuta este script en el SQL Editor de Supabase

-- 1. Crear tabla para historial de conversaciones
CREATE TABLE IF NOT EXISTS conversation_history (
  id BIGSERIAL PRIMARY KEY,
  conversation_id INTEGER NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  metadata JSONB DEFAULT '{}'::jsonb,

  -- Constraints
  CONSTRAINT content_not_empty CHECK (char_length(content) > 0)
);

-- 2. Crear índices para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_conversation_id
  ON conversation_history(conversation_id);

CREATE INDEX IF NOT EXISTS idx_created_at
  ON conversation_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversation_created
  ON conversation_history(conversation_id, created_at DESC);

-- 3. Habilitar Row Level Security (RLS)
ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;

-- 4. Crear política para permitir todas las operaciones (ajusta según tus necesidades)
-- NOTA: En producción, deberías usar políticas más restrictivas
CREATE POLICY "Enable all operations for service role"
  ON conversation_history
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- 5. Crear función para limpiar conversaciones antiguas (opcional)
CREATE OR REPLACE FUNCTION cleanup_old_conversations(days_old INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  DELETE FROM conversation_history
  WHERE created_at < NOW() - (days_old || ' days')::INTERVAL;

  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- 6. Crear vista para estadísticas de conversaciones
CREATE OR REPLACE VIEW conversation_stats AS
SELECT
  conversation_id,
  COUNT(*) as total_messages,
  COUNT(CASE WHEN role = 'user' THEN 1 END) as user_messages,
  COUNT(CASE WHEN role = 'assistant' THEN 1 END) as assistant_messages,
  MIN(created_at) as first_message,
  MAX(created_at) as last_message,
  MAX(created_at) - MIN(created_at) as conversation_duration
FROM conversation_history
GROUP BY conversation_id;

-- 7. Comentarios para documentación
COMMENT ON TABLE conversation_history IS 'Almacena el historial completo de conversaciones del chatbot';
COMMENT ON COLUMN conversation_history.conversation_id IS 'ID de la conversación de Chatwoot';
COMMENT ON COLUMN conversation_history.role IS 'Rol del mensaje: user (cliente) o assistant (bot)';
COMMENT ON COLUMN conversation_history.content IS 'Contenido del mensaje';
COMMENT ON COLUMN conversation_history.metadata IS 'Información adicional (modelo usado, fuente, etc.)';

-- 8. Información del curso/negocio (la lee la tool obtener_informacion_curso)
CREATE TABLE IF NOT EXISTS info_curso (
  id BIGSERIAL PRIMARY KEY,
  empresa TEXT NOT NULL,
  curso TEXT NOT NULL,
  precio TEXT,
  horario TEXT,
  duracion TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Datos de ejemplo: reemplázalos por los de tu negocio (solo si la tabla está vacía)
INSERT INTO info_curso (empresa, curso, precio, horario, duracion)
SELECT 'kittIA education', 'Creación de APIs Profesionales con FastAPI y Flask',
       '$350 USD', 'Martes y Jueves, 19:00-21:00 ET', '6 semanas'
WHERE NOT EXISTS (SELECT 1 FROM info_curso);

-- ============================================================================
-- CONSULTAS ÚTILES
-- ============================================================================

-- Ver últimos 10 mensajes de una conversación específica
-- SELECT * FROM conversation_history
-- WHERE conversation_id = 16
-- ORDER BY created_at DESC
-- LIMIT 10;

-- Ver estadísticas de todas las conversaciones
-- SELECT * FROM conversation_stats
-- ORDER BY last_message DESC;

-- Mensajes por día
-- SELECT
--   DATE(created_at) as date,
--   COUNT(*) as messages,
--   COUNT(DISTINCT conversation_id) as conversations
-- FROM conversation_history
-- GROUP BY DATE(created_at)
-- ORDER BY date DESC;

-- ============================================================================
-- COMPLETADO
-- ============================================================================
-- ✅ Tabla creada
-- ✅ Índices optimizados
-- ✅ RLS habilitado
-- ✅ Funciones de utilidad creadas
