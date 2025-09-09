import InfoCard from "@/shared/components/common/InfoCard";

interface NodeHoverCardProps {
  nodeId: string;
  nodeInfo: any;
}

export default function NodeHoverCard({
  nodeId,
  nodeInfo,
}: NodeHoverCardProps) {
  const content = (
    <>
      <div className="flex gap-1">
        <span className="font-sm text-muted-foreground">Address:</span>
        <span className="break-all">{nodeId}</span>
      </div>

      {nodeInfo === null || Object.keys(nodeInfo).length === 0 ? (
        <p className="text-muted-foreground">Loading node data...</p>
      ) : nodeInfo.error ? (
        <div className="text-foreground space-y-1 text-xs">
          <div>
            <span className="font-sm text-muted-foreground">Balance: </span>
            <span className="text-gray-400 italic">500</span>
          </div>
          <div>
            <span className="font-sm text-muted-foreground">Company: </span>
            <span className="text-gray-400 italic">CCinc</span>
          </div>
        </div>
      ) : (
        <div className="text-foreground space-y-1 text-sm">
          <div>
            <span className="font-sm text-muted-foreground">Balance:</span>
            <span>{nodeInfo.balance}</span>
          </div>
          <div>
            <span className="font-sm text-muted-foreground">Company:</span>
            <span>{nodeInfo.company}</span>
          </div>
        </div>
      )}
    </>
  );

  return (
    <InfoCard
      content={content}
      className="absolute bottom-5 left-5 max-w-sm min-w-[200px] text-[10px]"
    />
  );
}
