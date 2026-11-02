// "Maihemuti (Joe) Jiewulan" -> "MJ", 'Priya "P" Raman' -> "PR", "Madonna" -> "M".
// Nicknames in brackets/quotes are ignored, and only letters count, so punctuation
// can't become an initial. First letter of the first and last remaining words.
export function getInitials(name) {
  const withoutNicknames = name.replace(/\([^)]*\)|\[[^\]]*\]|"[^"]*"|“[^”]*”|'[^']*'/g, " ");
  const firstLetters = withoutNicknames
    .split(/\s+/)
    .map((word) => word.match(/\p{L}/u)?.[0])
    .filter(Boolean);
  if (firstLetters.length === 0) return "?";
  const initials = firstLetters.length === 1 ? firstLetters[0] : firstLetters[0] + firstLetters.at(-1);
  return initials.toUpperCase();
}
