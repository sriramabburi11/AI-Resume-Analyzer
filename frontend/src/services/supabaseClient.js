import { createClient } from '@supabase/supabase-js';

// Project defaults ensure production deployments never crash with a blank white screen
// even if environment variables are omitted from the hosting provider's dashboard.
const DEFAULT_SUPABASE_URL = 'https://mykmvgdrzvcoydpliwhr.supabase.co';
const DEFAULT_SUPABASE_ANON_KEY =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15a212Z2RyenZjb3lkcGxpd2hyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIwNTkxMTEsImV4cCI6MjEwNzYzNTExMX0.pHOXwng1vC6y_BhvLRYprftXl4QxRw3_xitZrkadOv0';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || DEFAULT_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || DEFAULT_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
