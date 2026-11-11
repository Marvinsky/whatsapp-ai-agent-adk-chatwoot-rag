# Configurar Supabase (historial persistente)

1. Crea un proyecto en https://supabase.com.
2. SQL Editor → pega y ejecuta `supabase_setup.sql`.
3. Settings → API: copia **Project URL** y la **service_role key** (backend) a `.env`:
   ```
   SUPABASE_URL=...
   SUPABASE_KEY=...
   ```
4. Verifica: tras una conversación, `select * from conversation_history order by created_at desc;`.

Si no defines estas variables, el bot funciona sin historial persistente.
