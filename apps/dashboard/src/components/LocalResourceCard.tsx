import type { ReactElement } from "react";
import type { LocalResource } from "../types/contract";

interface LocalResourceCardProps extends LocalResource {
  onConnect?: () => void;
}

export function LocalResourceCard({
  orgName,
  address,
  phone,
  onConnect,
}: LocalResourceCardProps): ReactElement {
  return (
    <article className="resource-card">
      <div className="resource-copy">
        <h4 className="resource-name">{orgName}</h4>
        <p className="resource-meta">{address}</p>
        <p className="resource-phone">{phone}</p>
      </div>
      <button
        type="button"
        className="btn-outline resource-connect"
        onClick={onConnect}
      >
        연결하기
      </button>
    </article>
  );
}
