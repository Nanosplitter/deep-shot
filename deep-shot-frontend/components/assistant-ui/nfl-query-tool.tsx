import type { ToolCallMessagePartComponent } from "@assistant-ui/react";
import {
  CheckIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  CodeIcon,
} from "lucide-react";
import { useState } from "react";
import { useSettings } from "@/lib/settings-context";

interface NFLQueryArgs {
  code: string;
  attempts: number;
  used_fallback: boolean;
}

export const NFLQueryTool: ToolCallMessagePartComponent<NFLQueryArgs> = ({
  args,
  result,
}) => {
  const [isCollapsed, setIsCollapsed] = useState(true);
  const { settings } = useSettings();

  // Only show in debug mode
  if (!settings.debugMode) {
    return null;
  }

  if (!args?.code) {
    return null;
  }

  return (
    <div className="my-4 flex w-full flex-col gap-2 rounded-lg border border-border/50 bg-muted/30">
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="flex items-center gap-2 rounded-lg px-4 py-3 text-left transition-colors hover:bg-muted/50"
      >
        <CodeIcon className="size-4 text-muted-foreground" />
        <span className="flex-grow text-sm font-medium text-muted-foreground">
          View Generated Code
        </span>
        {args.attempts > 1 && (
          <span className="mr-2 text-xs text-muted-foreground/70">
            {args.attempts} attempts
          </span>
        )}
        {args.used_fallback && (
          <span className="mr-2 text-xs text-amber-600 dark:text-amber-400">
            fallback model
          </span>
        )}
        {isCollapsed ? (
          <ChevronDownIcon className="size-4 text-muted-foreground" />
        ) : (
          <ChevronUpIcon className="size-4 text-muted-foreground" />
        )}
      </button>

      {!isCollapsed && (
        <div className="flex flex-col gap-3 border-t border-border/50 px-4 py-3">
          <div className="relative">
            <pre className="overflow-x-auto rounded-md bg-zinc-950 p-4 text-sm text-zinc-100 dark:bg-zinc-900">
              <code className="language-python">{args.code}</code>
            </pre>
          </div>

          {result !== undefined && result !== null && (
            <div className="border-t border-border/50 pt-3">
              <p className="mb-2 flex items-center gap-2 text-sm font-medium text-muted-foreground">
                <CheckIcon className="size-4 text-green-600 dark:text-green-400" />
                Raw Data
              </p>
              <pre className="overflow-x-auto rounded-md bg-zinc-100 p-3 text-xs text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200">
                {typeof result === "string"
                  ? result
                  : JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
