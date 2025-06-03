library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;

entity pdm_handler is
  generic (
    clkdiv_ratio : natural := 40
  );
  port (
    aclk    : in std_logic;
    aresetn : in std_logic;

    in_mic     : in std_logic;
    in_lr_sel  : in std_logic;
    out_lr_sel : out std_logic;
    out_clk    : out std_logic;

    m_axis_tready : in std_logic;
    m_axis_tvalid : out std_logic;
    m_axis_tdata  : out std_logic_vector(0 downto 0)
  );
end entity pdm_handler;

architecture rtl of pdm_handler is

  signal clk_cnt       : unsigned(find_leftmost(to_unsigned(clkdiv_ratio / 2, 32), '1') downto 0);
  constant half_period : unsigned := to_unsigned(clkdiv_ratio / 2, clk_cnt'length);

  signal clk_queue : std_logic_vector(1 downto 0);
  constant clk_re  : clk_queue'subtype := "01";
  constant clk_fe  : clk_queue'subtype := "10";

begin

  out_lr_sel <= in_lr_sel;

  --------------------------------------------------------------------------------
  -- Clocking
  --------------------------------------------------------------------------------
  process (aclk)
  begin
    if rising_edge(aclk) then
      if aresetn = '0' then
        out_clk   <= '0';
        clk_cnt   <= half_period;
        clk_queue <= (others => '0');
      else
        clk_cnt                   <= clk_cnt - 1;
        out_clk                   <= clk_queue(clk_queue'high);
        clk_queue(clk_queue'high) <= clk_queue(clk_queue'low);

        if clk_cnt = 0 then
          clk_cnt                  <= half_period;
          clk_queue(clk_queue'low) <= not clk_queue(clk_queue'low);
        end if;
      end if;
    end if;
  end process;

  --------------------------------------------------------------------------------
  -- Data latching
  --------------------------------------------------------------------------------
  process (aclk)
  begin
    if rising_edge(aclk) then
      if aresetn = '0' then
        m_axis_tvalid <= '0';
        m_axis_tdata  <= "0";
      else
        if m_axis_tready = '1' and m_axis_tvalid = '1' then
          m_axis_tvalid <= '0';
        end if;

        if (in_lr_sel = '0' and clk_queue = clk_re) or (in_lr_sel = '1' and clk_queue = clk_fe) then
          m_axis_tdata(0) <= in_mic;
          m_axis_tvalid   <= '1';
        end if;
      end if;
    end if;
  end process;

end architecture;