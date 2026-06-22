export function crestUrl(apiFootballId: number | null | undefined): string | null {
  if (apiFootballId === null || apiFootballId === undefined) return null;
  return `https://media.api-sports.io/football/teams/${apiFootballId}.png`;
}
