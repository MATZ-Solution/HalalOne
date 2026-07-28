-- Rolling conversation summaries for the agent's long-term memory.
--
-- Each row is one summary generated when a session crossed the token threshold
-- and was compacted. `message_ids` is the ACCUMULATED set of chat_messages.id
-- values that this summary now stands in for (previous summary's ids + the ids
-- folded in this round). To rebuild an older session's context we take the
-- LATEST row (by created_at) and fetch only the chat_messages whose id is NOT in
-- message_ids — i.e. the verbatim tail the summary hasn't absorbed yet.
--
-- Assumes chat_sessions.session_id and chat_messages.id are uuid. If your
-- session_id column is text, change `session_id uuid` -> `session_id text`
-- below (the FK type must match chat_sessions.session_id).

create table if not exists public.chat_summaries (
    id           uuid primary key default gen_random_uuid(),
    session_id   uuid not null
                 references public.chat_sessions (session_id) on delete cascade,
    summary      text not null,
    message_ids  uuid[] not null default '{}',
    created_at   timestamptz not null default now()
);

-- "Latest summary for a session" is the hot read (session load + every trigger
-- check), so index session_id + created_at desc.
create index if not exists chat_summaries_session_created_idx
    on public.chat_summaries (session_id, created_at desc);
