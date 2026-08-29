import Link from "next/link";
import type { Neologismo } from "@/types";
import { Heart, ThumbsDown } from "lucide-react";

interface NeologismCardProps {
  neologismo: Neologismo;
  onLike: (id: number) => void;
  onDeslike: (id: number) => void;
}

export default function NeologismCard({
  neologismo,
  onLike,
  onDeslike,
}: NeologismCardProps) {
  const formattedDate = new Date(neologismo.data_criacao).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });

  return (
    <article className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden transition-shadow hover:shadow-md">
      <div className="p-5">
        <div className="flex items-center justify-between mb-4">
          <span className="inline-flex items-center text-[10px] font-bold uppercase tracking-wider text-purple-dark bg-purple-light px-3 py-1 rounded-full">
            {neologismo.classe_gramatical}
          </span>
          <time className="text-xs text-gray-400 font-medium">{formattedDate}</time>
        </div>

        <Link href={`/neologismo/${neologismo.id}`}>
          <h2 className="font-sans text-2xl font-bold text-gray-900 mb-1 hover:text-purple-dark transition-colors">
            {neologismo.titulo}
          </h2>
        </Link>

        {neologismo.tipologia && (
          <p className="text-xs font-medium text-purple-dark mb-2">
            {neologismo.tipologia}
          </p>
        )}

        <div className="bg-gray-50 rounded-xl p-3 mb-4">
          <p className="text-xs text-gray-500 italic leading-relaxed">
            &ldquo;{neologismo.contexto_uso}&rdquo;
          </p>
          {neologismo.contextos[0]?.link && (
            <a
              href={neologismo.contextos[0].link}
              target="_blank"
              rel="noreferrer"
              className="block truncate text-[10px] text-purple-dark font-medium mt-1 hover:underline"
            >
              {neologismo.contextos[0].link}
            </a>
          )}
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-gray-100">
          <div className="flex flex-wrap gap-1.5">
            {neologismo.tags.map((tag) => (
              <span
                key={tag}
                className="text-[10px] font-semibold uppercase tracking-wider text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full"
              >
                {tag}
              </span>
            ))}
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => onLike(neologismo.id)}
              className="flex items-center gap-1.5 text-gray-400 hover:text-red-400 transition-colors group"
            >
              <Heart className="w-4 h-4 group-hover:fill-red-400" />
              <span className="text-xs font-medium">{neologismo.total_likes}</span>
            </button>
            <button
              onClick={() => onDeslike(neologismo.id)}
              className="flex items-center gap-1.5 text-gray-400 hover:text-purple-primary transition-colors"
            >
              <ThumbsDown className="w-4 h-4" />
              <span className="text-xs font-medium">{neologismo.total_deslikes}</span>
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}
