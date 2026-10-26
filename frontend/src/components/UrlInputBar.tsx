import React, { useState } from 'react';
import { Link2, Sparkles, Loader2, ListMusic } from 'lucide-react';

interface UrlInputBarProps {
  onResolve: (input: string) => Promise<void>;
  isLoading: boolean;
}

export const UrlInputBar: React.FC<UrlInputBarProps> = ({ onResolve, isLoading }) => {
  const [input, setInput] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    await onResolve(input);
    setInput('');
  };

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-4 sm:p-5 shadow-xl">
      <div className="flex items-center gap-2 mb-3 text-xs font-medium text-zinc-400">
        <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
        <span>Paste Spotify Track, Playlist, or Album links (single or batch)</span>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-zinc-500">
            <Link2 className="w-4 h-4" />
          </div>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="https://open.spotify.com/playlist/... or /track/... or paste multiple URLs"
            rows={2}
            className="w-full pl-10 pr-4 py-2.5 bg-zinc-950/80 border border-zinc-800 rounded-xl text-zinc-100 placeholder-zinc-500 text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition resize-none"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="sm:w-44 flex items-center justify-center gap-2 px-5 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:bg-zinc-800 disabled:text-zinc-600 disabled:cursor-not-allowed text-black font-semibold text-sm transition shadow-lg shadow-emerald-500/10 active:scale-95"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Resolving...</span>
            </>
          ) : (
            <>
              <ListMusic className="w-4 h-4 stroke-[2.5]" />
              <span>Inspect & Queue</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
};
