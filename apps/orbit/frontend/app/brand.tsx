export function OrbitBrand({ inverse = false }: { inverse?: boolean }) {
  const src = inverse
    ? "/brand/orbit-logo-inverse.svg"
    : "/brand/orbit-logo.svg";

  return (
    <img
      className="orbit-logo"
      src={src}
      width={156}
      height={45}
      alt="Orbit"
      decoding="async"
    />
  );
}
