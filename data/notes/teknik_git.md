# Git İpuçları (ÖRNEK NOT)

## Günlük akış
`git status`, `git add -p`, `git commit -m "mesaj"`, `git push`. Yeni dal için `git switch -c ozellik`.

## Hata düzeltme
Son commit mesajını değiştirmek için `git commit --amend` kullanılır. Henüz push edilmediyse güvenlidir. Bir commit'i geri almak için `git revert <hash>` yeni bir ters commit üretir, geçmişi bozmaz.

## Stash
Yarım işi saklamak için `git stash`, geri getirmek için `git stash pop`.
