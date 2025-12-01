"use client";

import { SettingsIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useSettings } from "@/lib/settings-context";

export function SettingsDialog() {
  const { settings, updateSettings } = useSettings();

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="size-8">
          <SettingsIcon className="size-4" />
          <span className="sr-only">Settings</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Settings</DialogTitle>
          <DialogDescription>
            Configure your Deep Shot experience
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <label className="flex items-center justify-between gap-4">
            <div className="flex flex-col gap-1">
              <span className="text-sm font-medium">Debug Mode</span>
              <span className="text-xs text-muted-foreground">
                Show generated code and raw data for each query
              </span>
            </div>
            <input
              type="checkbox"
              checked={settings.debugMode}
              onChange={(e) => updateSettings({ debugMode: e.target.checked })}
              className="size-4 rounded border-gray-300"
            />
          </label>
        </div>
      </DialogContent>
    </Dialog>
  );
}
