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
        # musescore is the easiest way to visualize outputs; lilypond is powerful
      	pkgs.musescore
	pkgs.lilypond
	# we want a python environment
        pkgs.pipenv
      ];
    };
  };
}
