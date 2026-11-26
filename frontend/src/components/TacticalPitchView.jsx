import { deriveFormation } from "../lib/format";

const POSITION_ORDER = {
  home: ["GK", "DF", "MF", "FW"],
  away: ["FW", "MF", "DF", "GK"],
};

function groupRows(players, side) {
  if (!players.length) return [];

  const hasGrid = players.every(
    (player) => typeof player.grid_position === "string" && player.grid_position.includes(":"),
  );

  if (hasGrid) {
    const rows = new Map();
    for (const player of players) {
      const [row, column] = player.grid_position.split(":").map((value) => Number(value) || 0);
      if (!rows.has(row)) rows.set(row, []);
      rows.get(row).push({ ...player, _column: column });
    }
    const orderedRows = [...rows.entries()].sort(([a], [b]) =>
      side === "home" ? a - b : b - a,
    );
    return orderedRows.map(([, rowPlayers]) =>
      rowPlayers
        .sort((a, b) => a._column - b._column)
        .map(({ _column, ...player }) => player),
    );
  }

  return POSITION_ORDER[side]
    .map((position) => players.filter((player) => player.position === position))
    .filter((group) => group.length > 0);
}

function PlayerChip({ player, side }) {
  return (
    <div
      data-testid={`${side}-player`}
      className="flex w-[22%] min-w-0 flex-col items-center gap-0.5"
      title={player.name}
    >
      <span
        dir="ltr"
        className="flex h-7 w-7 items-center justify-center rounded-full border border-white/60 bg-white font-latin text-[10px] font-extrabold text-pitch-deep shadow-sm sm:h-8 sm:w-8 sm:text-xs"
      >
        {player.number}
      </span>
      <span
        dir="ltr"
        className="max-w-full truncate rounded bg-black/35 px-1 py-0.5 font-latin text-[7px] font-semibold leading-tight text-white sm:text-[9px]"
      >
        {player.name}
      </span>
    </div>
  );
}

function TeamRows({ players, side }) {
  const rows = groupRows(players, side);
  return (
    <div
      data-testid={`${side}-half`}
      className="flex h-1/2 flex-col justify-around px-1"
    >
      {rows.map((row, rowIndex) => (
        <div
          key={`${side}-row-${rowIndex}`}
          className="flex items-center justify-around gap-0.5"
        >
          {row.map((player) => (
            <PlayerChip key={player.id || `${player.name}-${player.number}`} player={player} side={side} />
          ))}
        </div>
      ))}
    </div>
  );
}

export default function TacticalPitchView({
  homeLineup = [],
  awayLineup = [],
  homeTeamName = "",
  awayTeamName = "",
  homeFormation,
  awayFormation,
}) {
  const resolvedHomeFormation = homeFormation || deriveFormation(homeLineup);
  const resolvedAwayFormation = awayFormation || deriveFormation(awayLineup);

  if (!homeLineup.length && !awayLineup.length) {
    return (
      <div
        data-testid="pitch-empty"
        className="rounded-2xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400"
      >
        لم يتم الإعلان عن التشكيلة بعد
      </div>
    );
  }

  return (
    <div
      dir="rtl"
      data-testid="tactical-pitch"
      className="rounded-3xl border border-pitch-deep/70 bg-pitch-deep p-3 shadow-player sm:p-4"
    >
      <div className="mb-2 flex items-center justify-between px-1 text-xs font-bold text-white/90 sm:text-sm">
        <span>{homeTeamName}</span>
        <span
          data-testid="home-formation"
          dir="ltr"
          className="rounded-full bg-white/15 px-2.5 py-0.5 font-latin text-[10px] sm:text-xs"
        >
          {resolvedHomeFormation}
        </span>
      </div>

      <div className="pitch" data-testid="pitch">
        <div aria-hidden="true" className="pitch-box pitch-box-top" />
        <div aria-hidden="true" className="pitch-box pitch-box-bottom" />
        <div aria-hidden="true" className="pitch-midline" />
        <div aria-hidden="true" className="pitch-circle" />

        <TeamRows players={homeLineup} side="home" />
        <TeamRows players={awayLineup} side="away" />
      </div>

      <div className="mt-2 flex items-center justify-between px-1 text-xs font-bold text-white/90 sm:text-sm">
        <span>{awayTeamName}</span>
        <span
          data-testid="away-formation"
          dir="ltr"
          className="rounded-full bg-white/15 px-2.5 py-0.5 font-latin text-[10px] sm:text-xs"
        >
          {resolvedAwayFormation}
        </span>
      </div>
    </div>
  );
}
