import { Card, PageHeader } from "@/components/ui";

export default function SpaceshipPage() {
  return (
    <div>
      <PageHeader
        title="🚀 The Spaceship (coming soon)"
        subtitle="The eventual immersive UI — placeholder route reserved in v1"
      />
      <Card>
        <p className="text-slate-300">
          The future UI will feel like a spaceship with different rooms:
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-6 text-sm text-slate-400">
          <li>Each <strong className="text-slate-200">business</strong> is a room you walk into.</li>
          <li><strong className="text-slate-200">Global areas</strong> are communal rooms (cost control, skill library, GitHub bay).</li>
          <li><strong className="text-slate-200">Agents</strong> are futuristic robot characters; their pose reflects state (sleeping, thinking, building, blocked).</li>
          <li>Clicking a robot opens its character sheet: status, skills, tools, MCP servers, permissions, cost, current work, history.</li>
          <li>A <strong className="text-slate-200">command deck</strong> is Sheriff S&apos;s station, where you converse and approve.</li>
        </ul>
        <p className="mt-6 text-sm text-slate-500">
          The v1 dashboard already feeds the data model the spaceship will use — no data
          plumbing rewrite required. See <code>docs/10-ui-vision.md</code>.
        </p>
      </Card>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {["🛰️ Command Deck", "🚪 Business Rooms", "💸 Cost Control Bay", "🧠 Skill Library"].map((room) => (
          <Card key={room} className="flex h-28 items-center justify-center text-center text-slate-300">
            {room}
          </Card>
        ))}
      </div>
    </div>
  );
}
