-- Supabase Migration: Email Verification Table & Profile Field
-- Run this in your Supabase SQL Editor: https://supabase.com/dashboard/project/mykmvgdrzvcoydpliwhr/sql

-- 1. Create email_verifications table
CREATE TABLE IF NOT EXISTS public.email_verifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT NOT NULL,
  otp_hash TEXT NOT NULL,
  purpose TEXT NOT NULL DEFAULT 'email_verification',
  attempts INTEGER NOT NULL DEFAULT 0,
  max_attempts INTEGER NOT NULL DEFAULT 5,
  expires_at TIMESTAMPTZ NOT NULL,
  consumed BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL,
  last_sent_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexes for fast query lookup and expiration purging
CREATE INDEX IF NOT EXISTS idx_email_verifications_lookup 
  ON public.email_verifications (email, purpose, consumed);

CREATE INDEX IF NOT EXISTS idx_email_verifications_expires 
  ON public.email_verifications (expires_at);

-- Enable Row Level Security (RLS)
ALTER TABLE public.email_verifications ENABLE ROW LEVEL SECURITY;

-- Backend operations use the service-role key which bypasses RLS
CREATE POLICY "Service role full access on email_verifications"
  ON public.email_verifications
  TO service_role
  USING (true)
  WITH CHECK (true);

-- 2. Add email_verified column to profiles if not present
ALTER TABLE public.profiles 
  ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;

-- 3. Explicit Backward-Compatible Migration for Existing Users:
-- Existing users confirmed in Supabase Auth (confirmed_at IS NOT NULL) are marked verified
UPDATE public.profiles p
SET email_verified = TRUE
FROM auth.users u
WHERE p.id = u.id AND u.confirmed_at IS NOT NULL;
