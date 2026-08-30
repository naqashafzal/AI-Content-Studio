import os

pages = {
    'brand': ('Brand Assets', 'Manage your brand logos, colors, and intros.'),
    'history': ('History & Projects', 'View your previously generated content.'),
    'publish': ('Publish & SEO', 'Auto-publish to YouTube, TikTok, and Instagram.'),
    'tools': ('Video Tools', 'Utility tools for audio, TTS, and video manipulation.')
}

template = """export default function Page() {
  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-500">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white tracking-tight">{title}</h1>
        <p className="text-zinc-400 mt-1">{desc}</p>
      </div>
      <div className="glass-card p-12 text-center text-zinc-500">
        <p>Coming Soon</p>
      </div>
    </div>
  );
}"""

for folder, (title, desc) in pages.items():
    path = f'web/src/app/{folder}/page.tsx'
    os.makedirs(os.path.dirname(path), exist_ok=True)
    content = template.replace('{title}', title).replace('{desc}', desc)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
