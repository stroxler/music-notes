{
  description = "A simple flake for python and music";
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/release-23.11";
  };
  outputs = {
    self,
    nixpkgs,
  }: let
    system = "aarch64-darwin";
    pkgs = import nixpkgs {inherit system;};
  in {
    devShell.${system} = pkgs.mkShell {
      buildInputs = [
      	pkgs.ffmpeg_5
      ];
    };
  };
}
