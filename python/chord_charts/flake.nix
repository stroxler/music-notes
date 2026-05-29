{
  description = "A simple flake for python and music";
  inputs = {
    nixpkgs_u.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    nixpkgs.url = "github:NixOS/nixpkgs/release-24.05";
  };
  outputs = {
    self,
    nixpkgs,
    nixpkgs_u,
  }: let
    system = "aarch64-darwin";
    pkgs = import nixpkgs {inherit system;};
    pkgs_u = import nixpkgs_u {inherit system;};
  in {
    devShell.${system} = pkgs.mkShell {
      buildInputs = [
        pkgs_u.uv
        pkgs.lilypond
      ];
    };
  };
}
