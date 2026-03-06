import type { NewsArticle } from "@/types";

const SENTIMENT_COLORS = {
  positive: "text-green-400",
  neutral: "text-gray-400",
  negative: "text-red-400",
};

const SENTIMENT_DOTS = {
  positive: "bg-green-400",
  neutral: "bg-gray-600",
  negative: "bg-red-400",
};

export function NewsTimeline({ articles }: { articles: NewsArticle[] }) {
  return (
    <div className="space-y-3">
      {articles.map((article, i) => (
        <div key={i} className="flex gap-3 text-sm">
          <div className="flex flex-col items-center mt-1.5">
            <div className={`w-2 h-2 rounded-full ${SENTIMENT_DOTS[article.sentiment ?? "neutral"]}`} />
            {i < articles.length - 1 && <div className="w-px flex-1 bg-gray-800 mt-1" />}
          </div>
          <div className="flex-1 pb-3">
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-200 hover:text-blue-400 transition-colors"
            >
              {article.headline}
            </a>
            <div className="flex items-center gap-3 mt-1 text-xs">
              <span className="text-gray-500">{article.source}</span>
              <span className="text-gray-600">
                {new Date(article.published_at).toLocaleDateString()}
              </span>
              {article.sentiment && (
                <span className={SENTIMENT_COLORS[article.sentiment]}>
                  {article.sentiment}
                  {article.sentiment_confidence != null && (
                    <span className="text-gray-600 ml-1">
                      ({(article.sentiment_confidence * 100).toFixed(0)}%)
                    </span>
                  )}
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
