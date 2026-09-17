"""Original functional-test exercises. Helpers perform actions; assertions are model code."""
def examples(numbers):
    rows=[]
    for n in numbers:
        p=f'P{n}'; t=f'T{n}'
        items=[
            ('login',f'Login viewer {n}, /me 200, logout, /me 401.',
             'await h.login("viewer");expect(await h.me()).toBe(200);await h.logout();expect(await h.me()).toBe(401);'),
            ('password',f'Senhas {n}: tamanhos 11,12,128,129 retornam 400,201,201,400.',
             f'expect(await h.password({n},[11,12,128,129])).toEqual([400,201,201,400]);'),
            ('permissions',f'Projeto {p}: sprint viewer 403 e manager 201.',
             f'const p=await h.project("{p}");expect(await h.sprint(p,"viewer")).toBe(403);expect(await h.sprint(p,"manager")).toBe(201);'),
            ('workflow',f'Projeto {p}, tarefa {t}: concluir, recarregar, status done.',
             f'const p=await h.project("{p}");const t=await h.issue(p,"{t}");await h.done(t);await h.reload(p);expect(await h.status(t)).toBe("done");'),
            ('wip',f'Kanban {p}, limite 2, um ativo: disputar vaga, 201 e 409.',
             f'const p=await h.kanban("{p}",2);await h.active(p);expect((await Promise.all([h.active(p),h.active(p)])).sort()).toEqual([201,409]);'),
            ('metrics',f'Projeto {p}, tarefa {t}: iniciar e concluir, entregas 1.',
             f'const p=await h.project("{p}");const t=await h.issue(p,"{t}");await h.progress(t);await h.done(t);expect(await h.throughput(p)).toBe(1);'),
            ('mobile',f'Quadro {p} em 390x844: sem rolagem horizontal.',
             f'await h.board("{p}");await page.setViewportSize({{width:390,height:844}});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);'),
            ('recovery',f'Projeto {p}, tarefa {t}: reiniciar API, status todo.',
             f'const p=await h.project("{p}");const t=await h.issue(p,"{t}");await h.restart();expect(await h.status(t)).toBe("todo");'),
            ('sprint',f'Projeto {p}: criar sprint, iniciar 200, encerrar 200.',
             f'const p=await h.project("{p}");const s=await h.newSprint(p);expect(await h.start(s)).toBe(200);expect(await h.finish(s)).toBe(200);'),
        ]
        for kind,contract,answer in items:
            rows.append({'id':f'{kind}-{n}','kind':kind,'number':n,'prompt':'Teste JS h: '+contract+'\n','answer':answer})
    return rows
