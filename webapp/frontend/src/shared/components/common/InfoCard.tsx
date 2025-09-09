// components/common/InfoCard.tsx
import React from "react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/shared/components/ui/card";

interface InfoCardProps {
  title?: string;
  header?: React.ReactNode;
  content: React.ReactNode;
  className?: string;
}

export default function InfoCard({
  title,
  header,
  content,
  className = "",
}: InfoCardProps) {
  return (
    <Card
      className={`z-50 w-fit shadow-lg ${className}`}
      style={{
        backgroundColor: "#fcfcf7",
        backdropFilter: "blur(8px)",
        border: "1px solid #497D74",
        borderRadius: "6px",
        padding: "6px",
        textAlign: "left",
        fontSize: "12px",
        boxShadow: "0 0 2px 0 rgba(0, 0, 0, 0.1)",
      }}
    >
      {(title || header) && (
        <CardHeader className="m-0 space-y-1 pb-1">
          {title && (
            <CardTitle className="m-0 text-xs font-semibold text-gray-700">
              {title}
            </CardTitle>
          )}
          {header}
        </CardHeader>
      )}

      <CardContent className="text-muted-foreground space-y-2 px-2 pt-2 text-left text-[12px]">
        {content}
      </CardContent>
    </Card>
  );
}
