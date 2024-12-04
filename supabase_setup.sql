-- Enable the pg_trgm extension for text similarity search
create extension if not exists pg_trgm;

-- Create transcripts table
create table if not exists public.transcripts (
    id bigint primary key generated always as identity,
    video_id text unique not null,
    title text,
    transcript text,
    ai_summary text,
    created_at timestamp with time zone default timezone('utc'::text, now()),
    updated_at timestamp with time zone default timezone('utc'::text, now())
);

-- Create stories table
create table if not exists public.stories (
    id bigint primary key generated always as identity,
    title text not null,
    summary text not null,
    message text not null,
    created_at timestamp with time zone default timezone('utc'::text, now()),
    updated_at timestamp with time zone default timezone('utc'::text, now())
);

-- Create transcript_stories table for many-to-many relationship
create table if not exists public.transcript_stories (
    transcript_id bigint references public.transcripts(id),
    story_id bigint references public.stories(id),
    created_at timestamp with time zone default timezone('utc'::text, now()),
    primary key (transcript_id, story_id)
);

-- Create categories table
create table if not exists public.categories (
    transcript_id bigint primary key references public.transcripts(id),
    christian_life text[] default array[]::text[],
    church_ministry text[] default array[]::text[],
    theology text[] default array[]::text[],
    created_at timestamp with time zone default timezone('utc'::text, now()),
    updated_at timestamp with time zone default timezone('utc'::text, now())
);

-- Create indexes for better performance
create index if not exists idx_transcripts_video_id on public.transcripts(video_id);
create index if not exists idx_transcript_stories_story_id on public.transcript_stories(story_id);
create index if not exists idx_transcript_stories_transcript_id on public.transcript_stories(transcript_id);

-- Create a function to automatically update updated_at timestamp
create or replace function public.handle_updated_at()
returns trigger as $$
begin
    new.updated_at = timezone('utc'::text, now());
    return new;
end;
$$ language plpgsql;

-- Create triggers for updated_at
create trigger set_timestamp before update on public.transcripts
    for each row execute function public.handle_updated_at();

create trigger set_timestamp before update on public.stories
    for each row execute function public.handle_updated_at();

create trigger set_timestamp before update on public.categories
    for each row execute function public.handle_updated_at();

-- Enable Row Level Security (RLS)
alter table public.transcripts enable row level security;
alter table public.stories enable row level security;
alter table public.transcript_stories enable row level security;
alter table public.categories enable row level security;

-- Create policies for anonymous access (since we're using anon key)
create policy "Allow anonymous read access" on public.transcripts
    for select using (true);

create policy "Allow anonymous insert access" on public.transcripts
    for insert with check (true);

create policy "Allow anonymous update access" on public.transcripts
    for update using (true);

create policy "Allow anonymous read access" on public.stories
    for select using (true);

create policy "Allow anonymous insert access" on public.stories
    for insert with check (true);

create policy "Allow anonymous update access" on public.stories
    for update using (true);

create policy "Allow anonymous read access" on public.transcript_stories
    for select using (true);

create policy "Allow anonymous insert access" on public.transcript_stories
    for insert with check (true);

create policy "Allow anonymous update access" on public.transcript_stories
    for update using (true);

create policy "Allow anonymous read access" on public.categories
    for select using (true);

create policy "Allow anonymous insert access" on public.categories
    for insert with check (true);

create policy "Allow anonymous update access" on public.categories
    for update using (true);
