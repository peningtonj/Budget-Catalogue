import type { MeasureComponent } from '../../catalogue/types'


type ComponentTreeProps = {
  components: MeasureComponent[]
}


export function ComponentTree({ components }: ComponentTreeProps) {
  if (components.length === 0) {
    return <div className="detail-empty">No structured components extracted for this measure.</div>
  }

  const parentComponents = components.filter((component) => component.level === 1)
  const childComponents = components.filter((component) => component.level === 2)

  return (
    <div className="component-tree">
      {parentComponents.map((component) => {
        const children = childComponents.filter((child) => child.parent_component_id === component.id)
        return (
          <article className="component-card" key={component.id}>
            <div className="component-marker">•</div>
            <div>
              <p className="component-text">{component.component_text}</p>
              {component.amount_raw ? <p className="component-meta">{component.amount_raw}</p> : null}
              {children.length > 0 ? (
                <ul className="sub-component-list">
                  {children.map((child) => (
                    <li key={child.id}>
                      <span className="component-inline-marker">-</span>
                      <span>{child.component_text}</span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          </article>
        )
      })}
    </div>
  )
}
