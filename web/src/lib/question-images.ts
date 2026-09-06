/**
 * Resolve a question figure URL for <img src>.
 *
 * Paths in questions.json are like `/question_images/collegedunia/2022/q001.jpg`
 * and ship from `web/public/question_images` on Vercel.
 *
 * Optional CDN / Blob / Supabase Storage base:
 *   NEXT_PUBLIC_QUESTION_IMAGES_BASE_URL=https://….public.blob.vercel-storage.com
 */
export function questionImageSrc(src: string): string {
  const path = src.startsWith("/")
    ? src
    : src.startsWith("question_images/")
      ? `/${src}`
      : `/question_images/${src}`;
  const base = (process.env.NEXT_PUBLIC_QUESTION_IMAGES_BASE_URL || "").replace(
    /\/$/,
    "",
  );
  if (!base) return path;
  return `${base}${path}`;
}
