interface Props {
  chain?: string[];
  failure_chain?: string[];
}

function FailureChain({ chain, failure_chain }: Props) {
  const steps = chain || failure_chain || [];

  return (
    <div>
      <h2>🔗 Failure Chain</h2>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "8px" }}>
        {steps.map((step, index) => (
          <div key={index} style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div style={{
              border: "1px solid gray",
              padding: "12px",
              borderRadius: "10px",
              margin: "5px",
              width: "250px",
              textAlign: "center",
              backgroundColor: index === steps.length - 1 ? "#3a0000" : "#1a1a2e",
              color: index === steps.length - 1 ? "#ff4444" : "white",
              fontWeight: "bold"
            }}>
              {step}
            </div>
            {index < steps.length - 1 && (
              <div style={{ fontSize: "25px", margin: "5px", color: "#888" }}>↓</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default FailureChain;
