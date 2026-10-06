import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'Orbit · Projetos em movimento', description: 'Seu espaço local para planejar, acompanhar e entregar.' };
export default function RootLayout({children}:{children:React.ReactNode}) {return <html lang="pt-BR"><body>{children}</body></html>}
