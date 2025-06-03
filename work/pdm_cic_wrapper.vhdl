library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity pdm_cic_wrapper is
  generic (
    -- PDM generics
    clkdiv_ratio : natural := 40;

    -- CIC generics
    cic_order : positive range 1 to 7 := 1; -- M
    comb_taps : positive range 1 to 2 := 1; -- N
    dec_ratio : positive              := 64; -- R, expected to be power of 2

    compensate : boolean := false; -- enable compensator filter

    m_axis_data_width : positive := 8
  );
  port (
    aclk    : in std_logic;
    aresetn : in std_logic;

    -- PDM handler ports
    in_mic     : in std_logic;
    in_lr_sel  : in std_logic;
    out_lr_sel : out std_logic;
    out_clk    : out std_logic;

    -- CIC ports
    m_axis_tready : in std_logic;
    m_axis_tvalid : out std_logic;
    m_axis_tdata  : out std_logic_vector(m_axis_data_width - 1 downto 0)
  );
end entity pdm_cic_wrapper;

architecture rtl of pdm_cic_wrapper is

  signal pdm_cic_tready : std_logic;
  signal pdm_cic_tvalid : std_logic;
  signal pdm_cic_tdata  : std_logic_vector(0 downto 0);

begin

  pdm_handler_inst : entity work.pdm_handler
    generic map(
      clkdiv_ratio => clkdiv_ratio
    )
    port map
    (
      aclk          => aclk,
      aresetn       => aresetn,
      in_mic        => in_mic,
      in_lr_sel     => in_lr_sel,
      out_lr_sel    => out_lr_sel,
      out_clk       => out_clk,
      m_axis_tready => pdm_cic_tready,
      m_axis_tvalid => pdm_cic_tvalid,
      m_axis_tdata  => pdm_cic_tdata
    );

  cic_decimator_inst : entity work.cic_decimator
    generic map(
      cic_order         => cic_order,
      comb_taps         => comb_taps,
      dec_ratio         => dec_ratio,
      compensate        => compensate,
      s_axis_data_width => 1,
      m_axis_data_width => m_axis_data_width
    )
    port map
    (
      aclk          => aclk,
      aresetn       => aresetn,
      s_axis_tready => pdm_cic_tready,
      s_axis_tvalid => pdm_cic_tvalid,
      s_axis_tdata  => pdm_cic_tdata,
      m_axis_tready => m_axis_tready,
      m_axis_tvalid => m_axis_tvalid,
      m_axis_tdata  => m_axis_tdata
    );

end architecture;