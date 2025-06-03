library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;
use ieee.fixed_pkg.all;

entity sdft_resonator is
  generic (
    n_samples      : natural := 8;
    data_width     : natural := 25;
    coef_frac_bits : natural := 15;

    latency : natural range 0 to 1 := 1
  );
  port (
    clk   : in std_logic;
    reset : in std_logic;

    in_sample : in std_logic_vector(data_width - 1 downto 0);
    in_sine   : in std_logic_vector(2 + coef_frac_bits - 1 downto 0);
    in_cosine : in std_logic_vector(2 + coef_frac_bits - 1 downto 0);

    out_real : out std_logic_vector;
    out_im   : out std_logic_vector
  );
end entity sdft_resonator;

architecture rtl of sdft_resonator is

  signal sine   : sfixed(1 downto -coef_frac_bits);
  signal cosine : sfixed(1 downto -coef_frac_bits);

  constant gain_bits : natural := natural(ceil(log2(real(n_samples))));

begin

end architecture;