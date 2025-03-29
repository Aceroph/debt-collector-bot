let
  pkgs =
    import
      (fetchTarball "https://github.com/NixOS/nixpkgs/archive/f0946fa5f1fb876a9dc2e1850d9d3a4e3f914092.tar.gz")
      { };
in
pkgs.mkShell {
  packages = [
    (pkgs.python3.withPackages (
      python-pkgs: with python-pkgs; [
        discordpy
        asyncpg
        regex
      ]
    ))
  ];
}
